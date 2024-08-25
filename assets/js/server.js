const express = require('express');
const axios = require('axios');
const app = express();
const bodyParser = require('body-parser');
const moment = require('moment');
const { Buffer } = require('buffer');

app.use(bodyParser.json());
app.use(express.static('public'));

app.post('/mpesa-callback', (req, res) => {
    const mpesaResponse = req.body;

    console.log('Mpesa Callback Data: ', mpesaResponse);

    res.status(200).json({
        ResultCode: 0,
        ResultDesc: "Accepted"
    });
});

// const timestamp = moment().format(YYYYMMDDHHmmss);

app.use(express.json());

const consumerKey = 'uQpm1ycv00QqHfP84I0urOTKFOz7lrxDvcJ1vxAiHGwuqA0P';
const consumerSecret = 'rmXsLEA1scZoQybp0YjBDGKZvWMt0VhpidVkY2C1Ag3RfB0k7FXoUWsp5EY8kWGb';
const shortcode = '174379';
const passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919';
// const callbackURL = 'https://yourwebsite.com/mpesa-callback';  // Replace with your actual callback URL

// const password = Buffer.from(shortcode + passkey + timestamp).toString('base64');

// Get access token
async function getMpesaToken() {
    const auth = Buffer.from(`${consumerKey}:${consumerSecret}`).toString('base64');
    
    const response = await axios.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
        headers: {
            Authorization: `Basic ${auth}`
        }
    });
    
    return response.data.access_token;
}

// Send payment request
app.post('/process-mpesa-payment', async (req, res) => {
    const { phone, amount } = req.body;
    
    const token = await getMpesaToken();
    const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, -3);
    const password = Buffer.from(`${shortcode}${passkey}${timestamp}`).toString('base64');

    const requestBody = {
        BusinessShortCode: shortcode,
        Password: password,
        Timestamp: timestamp,
        TransactionType: 'CustomerPayBillOnline',
        Amount: amount,
        PartyA: phone, // Phone number initiating the payment
        PartyB: shortcode, // Your Paybill or Till number
        PhoneNumber: phone,
        CallBackURL: callbackURL,
        AccountReference: 'AlumniSupport', // Reference for the transaction
        TransactionDesc: 'Contribution for vulnerable students'
    };

    const response = await axios.post('https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest', requestBody, {
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });

    res.json({ success: true });
});

app.listen(3000, () => console.log('Server running on port 3000'));
