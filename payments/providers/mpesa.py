"""
M-Pesa Daraja API integration for Kenya payments.
Implements STK Push, C2B, transaction status, and reversals.
"""
import base64
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import json

logger = logging.getLogger('payments')


class MPesaProvider:
    """M-Pesa Daraja API integration."""
    
    def __init__(self, provider_account=None):
        """
        Initialize M-Pesa provider with credentials.
        
        Args:
            provider_account: ProviderAccount instance with M-Pesa credentials
        """
        if provider_account:
            self.consumer_key = provider_account.mpesa_consumer_key
            self.consumer_secret = provider_account.mpesa_consumer_secret
            self.shortcode = provider_account.mpesa_shortcode
            self.passkey = provider_account.mpesa_passkey
            self.environment = provider_account.mpesa_environment
        else:
            # Fall back to settings
            self.consumer_key = settings.MPESA_CONSUMER_KEY
            self.consumer_secret = settings.MPESA_CONSUMER_SECRET
            self.shortcode = settings.MPESA_SHORTCODE
            self.passkey = settings.MPESA_PASSKEY
            self.environment = settings.MPESA_ENVIRONMENT
        
        # Set API URLs based on environment
        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
        
        self.oauth_url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        self.stk_push_url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        self.query_url = f'{self.base_url}/mpesa/stkpushquery/v1/query'
        self.c2b_register_url = f'{self.base_url}/mpesa/c2b/v1/registerurl'
        self.transaction_status_url = f'{self.base_url}/mpesa/transactionstatus/v1/query'
        self.reversal_url = f'{self.base_url}/mpesa/reversal/v1/request'
        
        self._access_token = None
        self._token_expiry = None
    
    def get_access_token(self):
        """
        Get OAuth access token from M-Pesa API.
        Caches token until expiry.
        """
        # Return cached token if still valid
        if self._access_token and self._token_expiry:
            if timezone.now() < self._token_expiry:
                return self._access_token
        
        try:
            # Create basic auth header
            auth_string = f'{self.consumer_key}:{self.consumer_secret}'
            auth_bytes = auth_string.encode('utf-8')
            auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            headers = {
                'Authorization': f'Basic {auth_base64}',
            }
            
            response = requests.get(self.oauth_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data['access_token']
            
            # Token expires in 3600 seconds (1 hour), cache for 55 minutes to be safe
            self._token_expiry = timezone.now() + timedelta(minutes=55)
            
            logger.info('M-Pesa access token obtained successfully')
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to get M-Pesa access token: {str(e)}')
            raise Exception(f'M-Pesa authentication failed: {str(e)}')
    
    def generate_password(self):
        """
        Generate password for STK Push request.
        Password is base64(shortcode + passkey + timestamp)
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f'{self.shortcode}{self.passkey}{timestamp}'
        password_bytes = password_string.encode('utf-8')
        password_base64 = base64.b64encode(password_bytes).decode('utf-8')
        return password_base64, timestamp
    
    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_url):
        """
        Initiate STK Push (Lipa Na M-Pesa Online).
        
        Args:
            phone_number: Phone number in format 254XXXXXXXXX
            amount: Amount in KES (integer)
            account_reference: Reference for the transaction (max 12 chars)
            transaction_desc: Description of the transaction
            callback_url: URL to receive payment callback
            
        Returns:
            dict: Response from M-Pesa API with CheckoutRequestID and MerchantRequestID
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        # Ensure phone number is in correct format
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        # Ensure amount is integer (M-Pesa doesn't accept decimals)
        amount = int(Decimal(str(amount)))
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': amount,
            'PartyA': phone_number,
            'PartyB': self.shortcode,
            'PhoneNumber': phone_number,
            'CallBackURL': callback_url,
            'AccountReference': account_reference[:12],  # Max 12 characters
            'TransactionDesc': transaction_desc[:13],     # Max 13 characters
        }
        
        try:
            logger.info(f'Initiating M-Pesa STK Push: {phone_number}, KES {amount}')
            response = requests.post(
                self.stk_push_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f'M-Pesa STK Push initiated: {data}')
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa STK Push failed: {str(e)}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response: {e.response.text}')
            raise Exception(f'M-Pesa STK Push failed: {str(e)}')
    
    def query_stk_status(self, checkout_request_id):
        """
        Query STK Push transaction status.
        
        Args:
            checkout_request_id: CheckoutRequestID from STK Push initiation
            
        Returns:
            dict: Transaction status
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        }
        
        try:
            response = requests.post(
                self.query_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa status query failed: {str(e)}')
            raise Exception(f'M-Pesa status query failed: {str(e)}')
    
    def register_c2b_urls(self, validation_url, confirmation_url):
        """
        Register validation and confirmation URLs for C2B (PayBill/Till).
        
        Args:
            validation_url: URL to validate payment
            confirmation_url: URL to confirm payment
            
        Returns:
            dict: Registration response
        """
        access_token = self.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'ShortCode': self.shortcode,
            'ResponseType': 'Completed',  # or 'Cancelled'
            'ConfirmationURL': confirmation_url,
            'ValidationURL': validation_url,
        }
        
        try:
            response = requests.post(
                self.c2b_register_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            logger.info('M-Pesa C2B URLs registered successfully')
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa C2B registration failed: {str(e)}')
            raise Exception(f'M-Pesa C2B registration failed: {str(e)}')
    
    def query_transaction_status(self, transaction_id):
        """
        Query transaction status by transaction ID.
        
        Args:
            transaction_id: M-Pesa transaction ID
            
        Returns:
            dict: Transaction details
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'Initiator': 'apiuser',  # Your initiator name
            'SecurityCredential': password,
            'CommandID': 'TransactionStatusQuery',
            'TransactionID': transaction_id,
            'PartyA': self.shortcode,
            'IdentifierType': '4',  # 4 for shortcode
            'ResultURL': settings.MPESA_CALLBACK_URL,
            'QueueTimeOutURL': settings.MPESA_CALLBACK_URL,
            'Remarks': 'Status query',
            'Occasion': '',
        }
        
        try:
            response = requests.post(
                self.transaction_status_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa transaction status query failed: {str(e)}')
            raise Exception(f'Transaction status query failed: {str(e)}')
    
    def reverse_transaction(self, transaction_id, amount, remarks='Transaction reversal'):
        """
        Reverse a transaction (refund).
        
        Args:
            transaction_id: M-Pesa transaction ID to reverse
            amount: Amount to reverse
            remarks: Reason for reversal
            
        Returns:
            dict: Reversal response
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'Initiator': 'apiuser',
            'SecurityCredential': password,
            'CommandID': 'TransactionReversal',
            'TransactionID': transaction_id,
            'Amount': int(amount),
            'ReceiverParty': self.shortcode,
            'ReceiverIdentifierType': '11',  # 11 for shortcode
            'ResultURL': settings.MPESA_CALLBACK_URL,
            'QueueTimeOutURL': settings.MPESA_CALLBACK_URL,
            'Remarks': remarks,
            'Occasion': '',
        }
        
        try:
            response = requests.post(
                self.reversal_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f'M-Pesa reversal initiated for {transaction_id}')
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa reversal failed: {str(e)}')
            raise Exception(f'M-Pesa reversal failed: {str(e)}')
    
    @staticmethod
    def parse_callback(callback_data):
        """
        Parse M-Pesa callback data.
        
        Args:
            callback_data: JSON callback data from M-Pesa
            
        Returns:
            dict: Parsed transaction details
        """
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            parsed = {
                'result_code': result_code,
                'result_desc': result_desc,
                'merchant_request_id': merchant_request_id,
                'checkout_request_id': checkout_request_id,
                'success': result_code == 0,
            }
            
            # Parse callback metadata if payment was successful
            if result_code == 0:
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                
                for item in items:
                    name = item.get('Name')
                    value = item.get('Value')
                    
                    if name == 'Amount':
                        parsed['amount'] = Decimal(str(value))
                    elif name == 'MpesaReceiptNumber':
                        parsed['receipt_number'] = value
                    elif name == 'TransactionDate':
                        # Format: 20231215143022 (YYYYMMDDHHmmss)
                        parsed['transaction_date'] = value
                    elif name == 'PhoneNumber':
                        parsed['phone_number'] = value
            
            return parsed
            
        except Exception as e:
            logger.error(f'Failed to parse M-Pesa callback: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
