"""
Tests for M-Pesa payment provider.
"""
import pytest
from decimal import Decimal
from payments.providers.mpesa import MPesaProvider


@pytest.mark.unit
class TestMPesaProvider:
    """Test M-Pesa provider functionality."""
    
    def test_generate_password(self):
        """Test password generation for STK Push."""
        provider = MPesaProvider()
        provider.shortcode = '174379'
        provider.passkey = 'test_passkey'
        
        password, timestamp = provider.generate_password()
        
        assert password is not None
        assert len(password) > 0
        assert timestamp is not None
        assert len(timestamp) == 14  # YYYYMMDDHHmmss format
    
    def test_parse_callback_success(self):
        """Test parsing successful M-Pesa callback."""
        callback_data = {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': 'test-merchant-123',
                    'CheckoutRequestID': 'test-checkout-456',
                    'ResultCode': 0,
                    'ResultDesc': 'Success',
                    'CallbackMetadata': {
                        'Item': [
                            {'Name': 'Amount', 'Value': 1000},
                            {'Name': 'MpesaReceiptNumber', 'Value': 'ABC123'},
                            {'Name': 'TransactionDate', 'Value': 20231215100000},
                            {'Name': 'PhoneNumber', 'Value': 254712345678},
                        ]
                    }
                }
            }
        }
        
        parsed = MPesaProvider.parse_callback(callback_data)
        
        assert parsed['success'] is True
        assert parsed['result_code'] == 0
        assert parsed['amount'] == Decimal('1000')
        assert parsed['receipt_number'] == 'ABC123'
        assert parsed['phone_number'] == 254712345678
    
    def test_parse_callback_failure(self):
        """Test parsing failed M-Pesa callback."""
        callback_data = {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': 'test-merchant-123',
                    'CheckoutRequestID': 'test-checkout-456',
                    'ResultCode': 1032,
                    'ResultDesc': 'Request cancelled by user',
                }
            }
        }
        
        parsed = MPesaProvider.parse_callback(callback_data)
        
        assert parsed['success'] is False
        assert parsed['result_code'] == 1032
        assert parsed['result_desc'] == 'Request cancelled by user'
