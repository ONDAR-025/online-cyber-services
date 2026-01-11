"""
Flutterwave payment aggregator stub (disabled by default).
"""
import logging

logger = logging.getLogger('payments')


class FlutterwaveProvider:
    """Flutterwave payment aggregator stub."""
    
    def __init__(self, provider_account=None):
        """Initialize Flutterwave provider stub."""
        logger.warning('Flutterwave provider is a stub and not fully implemented')
        self.enabled = False
    
    def initiate_payment(self, amount, reference, callback_url):
        """Initiate payment via Flutterwave."""
        raise NotImplementedError('Flutterwave integration not implemented in v1')
    
    def query_transaction(self, transaction_id):
        """Query Flutterwave transaction status."""
        raise NotImplementedError('Flutterwave integration not implemented in v1')
