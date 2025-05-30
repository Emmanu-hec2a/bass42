from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json
import os
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
import secrets
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

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
    # Create directories
    os.makedirs('templates', exist_ok=True)
    
    # Initialize data files
    if not os.path.exists(ANNOUNCEMENTS_FILE):
        save_announcements([])
    
    if not os.path.exists(DONATIONS_FILE):
        save_donations([])

    if not os.path.exists(ALUMNI_DATA_FILE):
        save_alumni_data([])
    
    app.run(debug=True)