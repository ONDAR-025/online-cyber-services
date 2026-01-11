"""
Tests for Airtel Money payment provider.
"""
import pytest
from decimal import Decimal
from payments.providers.airtel import AirtelProvider


@pytest.mark.unit
class TestAirtelProvider:
    """Test Airtel Money provider functionality."""
    
    def test_parse_callback_success(self):
        """Test parsing successful Airtel callback."""
        callback_data = {
            'transaction': {
                'id': 'test-transaction-id',
                'airtel_money_id': 'AM123456789',
                'status': 'TS',  # Transaction Successful
                'amount': 1000,
                'currency': 'KES',
            },
            'subscriber': {
                'msisdn': '0712345678',
                'country': 'KE',
            }
        }
        
        parsed = AirtelProvider.parse_callback(callback_data)
        
        assert parsed['success'] is True
        assert parsed['status'] == 'TS'
        assert parsed['amount'] == Decimal('1000')
        assert parsed['currency'] == 'KES'
        assert parsed['phone_number'] == '0712345678'
    
    def test_parse_callback_failure(self):
        """Test parsing failed Airtel callback."""
        callback_data = {
            'transaction': {
                'id': 'test-transaction-id',
                'status': 'TF',  # Transaction Failed
                'amount': 1000,
                'currency': 'KES',
            }
        }
        
        parsed = AirtelProvider.parse_callback(callback_data)
        
        assert parsed['success'] is False
        assert parsed['status'] == 'TF'
