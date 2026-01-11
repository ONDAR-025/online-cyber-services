"""
Airtel Money API integration for Kenya payments.
Implements OAuth 2.0, Collect API, and webhook handling.
"""
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import json

logger = logging.getLogger('payments')


class AirtelProvider:
    """Airtel Money API integration."""
    
    def __init__(self, provider_account=None):
        """
        Initialize Airtel provider with credentials.
        
        Args:
            provider_account: ProviderAccount instance with Airtel credentials
        """
        if provider_account:
            self.client_id = provider_account.airtel_client_id
            self.client_secret = provider_account.airtel_client_secret
            self.environment = provider_account.airtel_environment
        else:
            # Fall back to settings
            self.client_id = settings.AIRTEL_CLIENT_ID
            self.client_secret = settings.AIRTEL_CLIENT_SECRET
            self.environment = settings.AIRTEL_ENVIRONMENT
        
        # Set API URLs based on environment
        if self.environment == 'production':
            self.base_url = 'https://openapiuat.airtel.africa'  # Change to production URL when available
        else:
            self.base_url = 'https://openapiuat.airtel.africa'
        
        self.auth_url = f'{self.base_url}/auth/oauth2/token'
        self.collect_url = f'{self.base_url}/merchant/v1/payments/'
        self.query_url = f'{self.base_url}/standard/v1/payments/'
        self.refund_url = f'{self.base_url}/standard/v1/payments/refund'
        
        self._access_token = None
        self._token_expiry = None
    
    def get_access_token(self):
        """
        Get OAuth 2.0 access token from Airtel API.
        Uses client credentials flow.
        """
        # Return cached token if still valid
        if self._access_token and self._token_expiry:
            if timezone.now() < self._token_expiry:
                return self._access_token
        
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            }
            
            response = requests.post(
                self.auth_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data['access_token']
            
            # Token typically expires in 3600 seconds, cache for 55 minutes
            expires_in = data.get('expires_in', 3600)
            self._token_expiry = timezone.now() + timedelta(seconds=expires_in - 300)
            
            logger.info('Airtel access token obtained successfully')
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to get Airtel access token: {str(e)}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response: {e.response.text}')
            raise Exception(f'Airtel authentication failed: {str(e)}')
    
    def initiate_collect(self, phone_number, amount, reference, callback_url):
        """
        Initiate Airtel Money collection (customer pays).
        
        Args:
            phone_number: Phone number in format 254XXXXXXXXX
            amount: Amount in KES
            reference: Transaction reference
            callback_url: URL to receive payment callback
            
        Returns:
            dict: Response from Airtel API with transaction ID
        """
        access_token = self.get_access_token()
        
        # Ensure phone number is in correct format (without country code for Airtel)
        if phone_number.startswith('254'):
            phone_number = '0' + phone_number[3:]
        elif phone_number.startswith('+254'):
            phone_number = '0' + phone_number[4:]
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Country': 'KE',
            'X-Currency': 'KES',
        }
        
        payload = {
            'reference': reference,
            'subscriber': {
                'country': 'KE',
                'currency': 'KES',
                'msisdn': phone_number,
            },
            'transaction': {
                'amount': float(amount),
                'country': 'KE',
                'currency': 'KES',
                'id': reference,
            },
        }
        
        try:
            logger.info(f'Initiating Airtel Money collect: {phone_number}, KES {amount}')
            response = requests.post(
                self.collect_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f'Airtel Money collect initiated: {data}')
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Airtel Money collect failed: {str(e)}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response: {e.response.text}')
            raise Exception(f'Airtel Money collect failed: {str(e)}')
    
    def query_transaction(self, transaction_id):
        """
        Query Airtel Money transaction status.
        
        Args:
            transaction_id: Airtel transaction ID
            
        Returns:
            dict: Transaction status
        """
        access_token = self.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Country': 'KE',
            'X-Currency': 'KES',
        }
        
        url = f'{self.query_url}{transaction_id}'
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Airtel transaction query failed: {str(e)}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response: {e.response.text}')
            raise Exception(f'Airtel transaction query failed: {str(e)}')
    
    def refund_transaction(self, transaction_id, amount):
        """
        Refund an Airtel Money transaction.
        
        Args:
            transaction_id: Original transaction ID
            amount: Amount to refund
            
        Returns:
            dict: Refund response
        """
        access_token = self.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Country': 'KE',
            'X-Currency': 'KES',
        }
        
        payload = {
            'transaction': {
                'airtel_money_id': transaction_id,
                'amount': float(amount),
                'country': 'KE',
                'currency': 'KES',
            },
        }
        
        try:
            logger.info(f'Initiating Airtel Money refund for {transaction_id}')
            response = requests.post(
                self.refund_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info(f'Airtel Money refund initiated')
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Airtel Money refund failed: {str(e)}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response: {e.response.text}')
            raise Exception(f'Airtel Money refund failed: {str(e)}')
    
    @staticmethod
    def parse_callback(callback_data):
        """
        Parse Airtel Money callback/webhook data.
        
        Args:
            callback_data: JSON callback data from Airtel
            
        Returns:
            dict: Parsed transaction details
        """
        try:
            transaction = callback_data.get('transaction', {})
            
            status = transaction.get('status')
            transaction_id = transaction.get('id')
            airtel_money_id = transaction.get('airtel_money_id')
            
            parsed = {
                'status': status,
                'transaction_id': transaction_id,
                'airtel_money_id': airtel_money_id,
                'success': status in ['TS', 'SUCCESS'],  # TS = Transaction Successful
            }
            
            # Parse transaction details
            if 'amount' in transaction:
                parsed['amount'] = Decimal(str(transaction['amount']))
            
            if 'currency' in transaction:
                parsed['currency'] = transaction['currency']
            
            # Parse subscriber details if available
            subscriber = callback_data.get('subscriber', {})
            if subscriber:
                parsed['phone_number'] = subscriber.get('msisdn')
                parsed['country'] = subscriber.get('country')
            
            return parsed
            
        except Exception as e:
            logger.error(f'Failed to parse Airtel callback: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_callback_signature(callback_data, signature, secret):
        """
        Verify Airtel webhook signature (if implemented).
        
        Args:
            callback_data: Raw callback data
            signature: Signature from Airtel header
            secret: Shared secret
            
        Returns:
            bool: True if signature is valid
        """
        # Note: Implement signature verification if Airtel provides it
        # For now, rely on HTTPS and source IP validation
        logger.warning('Airtel signature verification not implemented')
        return True
