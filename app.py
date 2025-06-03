from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json
import os
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import re
import sqlite3
from functools import wraps
import random
import string

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")

# M-Pesa Configuration
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL')

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# File paths
ANNOUNCEMENTS_FILE = 'announcements.json'
DONATIONS_FILE = 'donations.json'
ALUMNI_DATA_FILE = 'alumni_data.json'

def load_data(filename):
    """Load data from JSON file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def load_alumni_data():
    """Load existing alumni data from JSON file"""
    if os.path.exists(ALUMNI_DATA_FILE):
        try:
            with open(ALUMNI_DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_alumni_data(dat):
    """Save alumni data to JSON file"""
    try:
        with open(ALUMNI_DATA_FILE, 'w') as f:
            json.dump(dat, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def save_data(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_announcements():
    return load_data(ANNOUNCEMENTS_FILE)

def save_announcements(announcements):
    save_data(announcements, ANNOUNCEMENTS_FILE)

def load_donations():
    return load_data(DONATIONS_FILE)

def save_donations(donations):
    save_data(donations, DONATIONS_FILE)

def is_admin_logged_in():
    """Check if admin is logged in"""
    return session.get('admin_logged_in', False)

def validate_phone_number(phone):
    """Validate Kenyan phone number format"""
    # Remove any spaces or special characters
    phone = re.sub(r'[^\d]', '', phone)
    
    # Check if it's a valid Kenyan number
    if phone.startswith('254') and len(phone) == 12:
        return phone
    elif phone.startswith('0') and len(phone) == 10:
        return '254' + phone[1:]  # Convert 0xxx to 254xxx
    elif phone.startswith('7') and len(phone) == 9:
        return '254' + phone  # Convert 7xxx to 254xxx
    elif phone.startswith('1') and len(phone) == 9:
        return '254' + phone  # Convert 1xxx to 254xxx
    
    return None

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    try:
        url = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
        # For production, use: https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials
        
        credentials = base64.b64encode(f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('access_token')
        return None
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def initiate_mpesa_payment(phone, amount, account_ref, transaction_desc):
    """Initiate M-Pesa STK Push"""
    access_token = get_mpesa_access_token()
    if not access_token:
        return {'success': False, 'message': 'Failed to get access token'}
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Generate password
    password_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_string.encode()).decode()
    
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    # For production, use: https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'BusinessShortCode': MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(amount),
        'PartyA': phone,
        'PartyB': MPESA_SHORTCODE,
        'PhoneNumber': phone,
        'CallBackURL': MPESA_CALLBACK_URL,
        'AccountReference': account_ref,
        'TransactionDesc': transaction_desc
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {'success': False, 'message': f'Request failed: {str(e)}'}

# Routes
@app.route('/')
def index():
    """Display the main page with announcements"""
    announcements = load_announcements()
    return render_template('index.html', announcements=announcements)

@app.route('/support', methods=['GET', 'POST'])
def support():
    """Handle support/donation form"""
    if request.method == 'POST':
        # Handle AJAX request
        data = request.get_json()
        
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        
        # Validation
        if not name or not phone or not amount:
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        # Validate phone number
        validated_phone = validate_phone_number(phone)
        if not validated_phone:
            return jsonify({'success': False, 'message': 'Invalid phone number format'})
        
        # Validate amount
        try:
            amount = float(amount)
            if amount < 1:
                return jsonify({'success': False, 'message': 'Amount must be at least KES 1'})
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        # Generate unique reference
        reference = f"SCH{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(1000):03d}"
        
        # Save donation record (pending)
        donations = load_donations()
        donation_record = {
            'id': len(donations) + 1,
            'reference': reference,
            'name': name,
            'phone': validated_phone,
            'amount': amount,
            'status': 'pending',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mpesa_receipt': None
        }
        donations.append(donation_record)
        save_donations(donations)
        
        # Initiate M-Pesa payment
        mpesa_response = initiate_mpesa_payment(
            validated_phone,
            amount,
            reference,
            f"School Support - {name}"
        )
        
        if mpesa_response.get('ResponseCode') == '0':
            return jsonify({
                'success': True,
                'message': 'Payment request sent to your phone. Please complete the transaction.',
                'checkout_request_id': mpesa_response.get('CheckoutRequestID')
            })
        else:
            # Update donation status to failed
            donation_record['status'] = 'failed'
            donation_record['error'] = mpesa_response.get('errorMessage', 'Unknown error')
            save_donations(donations)
            
            return jsonify({
                'success': False,
                'message': f"Payment initiation failed: {mpesa_response.get('errorMessage', 'Unknown error')}"
            })
    
    return render_template('support.html')

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback"""
    try:
        callback_data = request.get_json()
        
        # Extract relevant information
        result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        
        if result_code == 0:  # Success
            # Extract transaction details
            callback_metadata = callback_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
            
            amount = None
            mpesa_receipt = None
            phone = None
            
            for item in callback_metadata:
                if item.get('Name') == 'Amount':
                    amount = item.get('Value')
                elif item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt = item.get('Value')
                elif item.get('Name') == 'PhoneNumber':
                    phone = item.get('Value')
            
            # Update donation status
            donations = load_donations()
            for donation in donations:
                if donation['phone'] == str(phone) and donation['amount'] == amount and donation['status'] == 'pending':
                    donation['status'] = 'completed'
                    donation['mpesa_receipt'] = mpesa_receipt
                    donation['completed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    break
            
            save_donations(donations)
        else:
            # Payment failed - update status
            donations = load_donations()
            for donation in donations:
                if donation['status'] == 'pending':  # This is a simple matching - you might want to improve this
                    donation['status'] = 'failed'
                    donation['error'] = 'Payment was cancelled or failed'
                    break
            save_donations(donations)
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    
    except Exception as e:
        print(f"Callback error: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'})

# Database setup
def init_db():
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    
    # Teachers table
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        registration_code TEXT,
        is_approved BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Admin registration codes table
    c.execute('''CREATE TABLE IF NOT EXISTS registration_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        is_used BOOLEAN DEFAULT 0,
        created_by TEXT,
        used_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP,
        FOREIGN KEY (used_by) REFERENCES teachers (id)
    )''')
    
    # Pre-approved email domains/addresses
    c.execute('''CREATE TABLE IF NOT EXISTS approved_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        added_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        content TEXT NOT NULL,
        reply_to INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES teachers (id),
        FOREIGN KEY (reply_to) REFERENCES messages (id)
    )''')
    
    # Reactions table
    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        teacher_id INTEGER,
        reaction TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_id) REFERENCES messages (id),
        FOREIGN KEY (teacher_id) REFERENCES teachers (id),
        UNIQUE(message_id, teacher_id, reaction)
    )''')
    
    # Insert some sample registration codes (remove in production)
    c.execute('''INSERT OR IGNORE INTO registration_codes (code, created_by) VALUES 
                 ('BISHOP2024TEACH', 'admin'),
                 ('ABIERO2024STAFF', 'admin'),
                 ('TEACH2024BISHOP', 'admin')''')
    
    # Insert school email domain pattern
    c.execute('''INSERT OR IGNORE INTO approved_emails (email, added_by) VALUES 
                 ('%@bishopabiero.ac.ke', 'admin'),
                 ('%@bishopabiero.edu', 'admin')''')

    # Add this to create the missing column
    # c.execute('ALTER TABLE teachers ADD COLUMN registration_code TEXT')

    
    conn.commit()
    conn.close()

# Helper functions for validation
def is_valid_school_email(email):
    """Check if email belongs to Bishop Abiero school"""
    school_domains = ['@bishopabiero.ac.ke', '@bishopabiero.edu', '@bishopabiero.sch.ke']
    return any(email.lower().endswith(domain) for domain in school_domains)

def is_pre_approved_email(email):
    """Check if email is in pre-approved list"""
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM approved_emails WHERE email = ? OR ? LIKE email', 
              (email.lower(), email.lower()))
    result = c.fetchone()[0] > 0
    conn.close()
    return result

def validate_registration_code(code):
    """Check if registration code is valid and unused"""
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('SELECT id FROM registration_codes WHERE code = ? AND is_used = 0', (code,))
    result = c.fetchone()
    conn.close()
    return result is not None

def use_registration_code(code, teacher_id):
    """Mark registration code as used"""
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('''UPDATE registration_codes 
                 SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP 
                 WHERE code = ?''', (teacher_id, code))
    conn.commit()
    conn.close()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            return redirect(url_for('login'))
        
        # Check if teacher is approved
        conn = sqlite3.connect('teachers_portal.db')
        c = conn.cursor()
        c.execute('SELECT is_approved FROM teachers WHERE id = ?', (session['teacher_id'],))
        result = c.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return render_template('pending_approval.html')
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/teachers/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('teachers_portal.db')
        c = conn.cursor()
        c.execute('SELECT id, first_name, is_approved FROM teachers WHERE email = ? AND password = ?', 
                 (email, password))
        teacher = c.fetchone()
        conn.close()
        
        if teacher:
            if teacher[2]:  # is_approved
                session['teacher_id'] = teacher[0]
                session['teacher_name'] = teacher[1]
                return redirect(url_for('chat'))
            else:
                return render_template('login.html', error='Account pending approval. Please contact admin.')
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/teachers/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        email = request.form['email'].lower()
        password = request.form['password']
        registration_code = request.form.get('registration_code', '').strip()
        
        # Validation checks
        errors = []
        
        # Check email domain
        if not is_valid_school_email(email) and not is_pre_approved_email(email):
            errors.append('Only Bishop Abiero school email addresses are allowed')
        
        # Check registration code if provided
        if registration_code:
            if not validate_registration_code(registration_code):
                errors.append('Invalid or already used registration code')
        else:
            # If no registration code, require school email
            if not is_valid_school_email(email):
                errors.append('Registration code is required for non-school email addresses')
        
        if errors:
            return render_template('register.html', errors=errors)
        
        conn = sqlite3.connect('teachers_portal.db')
        c = conn.cursor()
        try:
            # Determine approval status
            is_approved = 1 if is_valid_school_email(email) or registration_code else 0
            
            c.execute('''INSERT INTO teachers (first_name, email, password, registration_code, is_approved) 
                         VALUES (?, ?, ?, ?, ?)''',
                     (first_name, email, password, registration_code, is_approved))
            teacher_id = c.lastrowid
            
            # Use registration code if provided
            if registration_code:
                use_registration_code(registration_code, teacher_id)
            
            conn.commit()
            
            if is_approved:
                return redirect(url_for('login'))
            else:
                return render_template('registration_success.html', message='Registration successful! Please wait for admin approval.')
                
        except sqlite3.IntegrityError:
            return render_template('register.html', errors=['Email already exists'])
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/teachers/chat')
@login_required
@approved_required
def chat():
    if 'teacher_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    
    # Check if teacher is approved
    c.execute('SELECT is_approved FROM teachers WHERE id = ?', (session['teacher_id'],))
    teacher = c.fetchone()
    
    if not teacher or not teacher[0]:
        return render_template('pending_approval.html')  # Create this template
    
    conn.close()
    # return render_template('chat.html')
    return render_template('chat.html', teacher_name=session['teacher_name'])

@app.route('/teachers/admin')
@login_required
def admin_panel():
    # Simple admin check - you can enhance this
    if session.get('teacher_name') != 'Admin':  # Replace with proper admin check
        return redirect(url_for('chat'))
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    
    # Get pending approvals
    c.execute('''SELECT id, first_name, email, registration_code, created_at 
                 FROM teachers WHERE is_approved = 0''')
    pending_teachers = c.fetchall()
    
    # Get unused registration codes
    c.execute('''SELECT code, created_by, created_at FROM registration_codes 
                 WHERE is_used = 0''')
    unused_codes = c.fetchall()

    # Get approved teachers
    c.execute('''SELECT id, first_name, email, registration_code, created_at 
                 FROM teachers WHERE is_approved = 1''')
    approved_teachers = c.fetchall()
    
    conn.close()
    
    return render_template('admin.html', 
                         pending_teachers=pending_teachers, 
                         unused_codes=unused_codes)

@app.route('/teachers/admin/approve/<int:teacher_id>')
@login_required
def approve_teacher(teacher_id):
    if session.get('teacher_name') != 'Admin':  # Replace with proper admin check
        return redirect(url_for('chat'))
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('UPDATE teachers SET is_approved = 1 WHERE id = ?', (teacher_id,))
    conn.commit()
    conn.close()
    
    flash('Teacher approved successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/reject/<int:teacher_id>')
def reject_teacher(teacher_id):
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    
    # You can either delete the record or mark as rejected
    c.execute('DELETE FROM teachers WHERE id = ?', (teacher_id,))
    conn.commit()
    conn.close()
    
    flash('Teacher rejected and removed!', 'success')
    return redirect(url_for('admin'))

@app.route('/teachers/admin/generate-code', methods=['POST'])
@login_required
def generate_code():
    if session.get('teacher_name') != 'Admin':  # Replace with proper admin check
        return redirect(url_for('chat'))
    
    # Generate random code
    code = 'BISHOP' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('INSERT INTO registration_codes (code, created_by) VALUES (?, ?)',
             (code, session['teacher_name']))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin'))

@app.route('/teachers/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# API Routes
@app.route('/api/messages')
@login_required
def get_messages():
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('''
        SELECT m.id, m.content, m.reply_to, m.created_at, t.first_name,
               GROUP_CONCAT(r.reaction || ':' || COUNT(r.reaction)) as reactions
        FROM messages m
        JOIN teachers t ON m.sender_id = t.id
        LEFT JOIN reactions r ON m.id = r.message_id
        GROUP BY m.id
        ORDER BY m.created_at ASC
    ''')
    messages = []
    for row in c.fetchall():
        reactions = {}
        if row[5]:
            for reaction_data in row[5].split(','):
                reaction, count = reaction_data.split(':')
                reactions[reaction] = int(count)
        
        messages.append({
            'id': row[0],
            'content': row[1],
            'reply_to': row[2],
            'created_at': row[3],
            'sender': row[4],
            'reactions': reactions
        })
    conn.close()
    return jsonify(messages)

@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    data = request.json
    content = data.get('content')
    reply_to = data.get('reply_to')
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (sender_id, content, reply_to) VALUES (?, ?, ?)',
             (session['teacher_id'], content, reply_to))
    message_id = c.lastrowid
    conn.commit()
    
    # Get the complete message data
    c.execute('''
        SELECT m.id, m.content, m.reply_to, m.created_at, t.first_name
        FROM messages m
        JOIN teachers t ON m.sender_id = t.id
        WHERE m.id = ?
    ''', (message_id,))
    message_data = c.fetchone()
    conn.close()
    
    message = {
        'id': message_data[0],
        'content': message_data[1],
        'reply_to': message_data[2],
        'created_at': message_data[3],
        'sender': message_data[4],
        'reactions': {}
    }
    
    # Broadcast to all connected clients
    socketio.emit('new_message', message)
    return jsonify(message)

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    # Only allow deletion of own messages
    c.execute('DELETE FROM messages WHERE id = ? AND sender_id = ?',
             (message_id, session['teacher_id']))
    conn.commit()
    
    if c.rowcount > 0:
        # Also delete associated reactions
        c.execute('DELETE FROM reactions WHERE message_id = ?', (message_id,))
        conn.commit()
        conn.close()
        
        # Broadcast deletion
        socketio.emit('message_deleted', {'message_id': message_id})
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'error': 'Message not found or unauthorized'}), 403

@app.route('/api/messages/<int:message_id>/react', methods=['POST'])
@login_required
def react_to_message(message_id):
    data = request.json
    reaction = data.get('reaction')
    
    conn = sqlite3.connect('teachers_portal.db')
    c = conn.cursor()
    
    # Check if reaction already exists
    c.execute('SELECT id FROM reactions WHERE message_id = ? AND teacher_id = ? AND reaction = ?',
             (message_id, session['teacher_id'], reaction))
    existing = c.fetchone()
    
    if existing:
        # Remove reaction
        c.execute('DELETE FROM reactions WHERE message_id = ? AND teacher_id = ? AND reaction = ?',
                 (message_id, session['teacher_id'], reaction))
    else:
        # Add reaction
        c.execute('INSERT INTO reactions (message_id, teacher_id, reaction) VALUES (?, ?, ?)',
                 (message_id, session['teacher_id'], reaction))
    
    conn.commit()
    
    # Get updated reaction counts
    c.execute('''
        SELECT reaction, COUNT(*) as count
        FROM reactions
        WHERE message_id = ?
        GROUP BY reaction
    ''', (message_id,))
    reactions = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    # Broadcast reaction update
    socketio.emit('reaction_updated', {
        'message_id': message_id,
        'reactions': reactions
    })
    
    return jsonify({'reactions': reactions})

# WebSocket events
@socketio.on('connect')
def on_connect():
    if 'teacher_id' in session:
        join_room('teachers')
        emit('status', {'msg': f"{session['teacher_name']} has connected"})

@socketio.on('disconnect')
def on_disconnect():
    if 'teacher_id' in session:
        leave_room('teachers')


@app.route('/admin')
def admin():
    """Admin panel"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    announcements = load_announcements()
    donations = load_donations()
    
    # ✅ ADD THIS: Load alumni data
    alumni = load_alumni_data()
    
    # Calculate donation statistics
    total_donations = sum(d['amount'] for d in donations if d['status'] == 'completed')
    successful_donations = len([d for d in donations if d['status'] == 'completed'])
    pending_donations = len([d for d in donations if d['status'] == 'pending'])
    
    # ✅ ADD THIS: Calculate alumni stats
    total_alumni = len(alumni)
    
    stats = {
        'total_amount': total_donations,
        'successful_count': successful_donations,
        'pending_count': pending_donations,
        'total_attempts': len(donations),
        'total_alumni': total_alumni  # ✅ Add this for the stats section
    }
    
    # ✅ ADD 'alumni=alumni' to the render_template call
    return render_template('admin.html', 
                         announcements=announcements, 
                         donations=donations, 
                         stats=stats,
                         alumni=alumni)  # ✅ This was missing!

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/add_announcement', methods=['POST'])
def add_announcement():
    """Add announcement"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    emoji = request.form.get('emoji', '📢')
    
    if title and content:
        announcements = load_announcements()
        new_announcement = {
            'id': len(announcements) + 1,
            'title': f"{emoji} {title}",
            'content': content,
            'date': datetime.now().strftime('%B %d, %Y')
        }
        announcements.insert(0, new_announcement)
        save_announcements(announcements)
        flash('Announcement added successfully!', 'success')
    
    return redirect(url_for('admin'))

@app.route('/delete_announcement/<int:announcement_id>')
def delete_announcement(announcement_id):
    """Delete announcement"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    announcements = load_announcements()
    announcements = [a for a in announcements if a['id'] != announcement_id]
    save_announcements(announcements)
    flash('Announcement deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/submit-alumni', methods=['POST'])
def submit_alumni():
    """Handle alumni form submission"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            dat = request.get_json()
        else:
            dat = request.form.to_dict()
        
        if not dat:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['alumni-name', 'alumni-phone', 'year-started', 'year-finished']
        for field in required_fields:
            if not dat.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate year fields
        try:
            year_started = int(dat['year-started'])
            year_finished = int(dat['year-finished'])
            
            if year_started < 1950 or year_started > 2030:
                return jsonify({'error': 'Year started must be between 1950 and 2030'}), 400
            
            if year_finished < 1950 or year_finished > 2030:
                return jsonify({'error': 'Year finished must be between 1950 and 2030'}), 400
            
            if year_finished < year_started:
                return jsonify({'error': 'Year finished cannot be earlier than year started'}), 400
                
        except ValueError:
            return jsonify({'error': 'Years must be valid numbers'}), 400
        
        # Load existing data
        alumni_data = load_alumni_data()
        
        # Create new alumni record
        new_alumni = {
            'id': len(alumni_data) + 1,
            'name': dat['alumni-name'].strip(),
            'phone': dat['alumni-phone'].strip(),
            'year_started': year_started,
            'year_finished': year_finished,
            'submitted_at': datetime.now().isoformat()
        }
        
        # Add to data list
        alumni_data.append(new_alumni)
        
        # Save to file
        if save_alumni_data(alumni_data):
            return jsonify({
                'message': 'Alumni registration submitted successfully',
                'alumni_id': new_alumni['id']
            }), 201
        else:
            return jsonify({'error': 'Failed to save data'}), 500
            
    except Exception as e:
        print(f"Error processing alumni submission: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/alumni-list', methods=['GET'])
def get_alumni_list():
    """Get list of all alumni (optional endpoint for viewing data)"""
    try:
        alumni_data = load_alumni_data()
        return jsonify({
            'alumni': alumni_data,
            'total': len(alumni_data)
        })
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve alumni data'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':

    init_db()
    # Create directories
    os.makedirs('templates', exist_ok=True)
    
    # Initialize data files
    if not os.path.exists(ANNOUNCEMENTS_FILE):
        save_announcements([])
    
    if not os.path.exists(DONATIONS_FILE):
        save_donations([])

    if not os.path.exists(ALUMNI_DATA_FILE):
        save_alumni_data([])
    
    # port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)