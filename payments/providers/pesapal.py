"""
Pesapal payment aggregator stub (disabled by default).
"""
import logging

logger = logging.getLogger('payments')


class PesapalProvider:
    """Pesapal payment aggregator stub."""
    
    def __init__(self, provider_account=None):
        """Initialize Pesapal provider stub."""
        logger.warning('Pesapal provider is a stub and not fully implemented')
        self.enabled = False
    
    def initiate_payment(self, amount, reference, callback_url):
        """Initiate payment via Pesapal."""
        raise NotImplementedError('Pesapal integration not implemented in v1')
    
    def query_transaction(self, transaction_id):
        """Query Pesapal transaction status."""
        raise NotImplementedError('Pesapal integration not implemented in v1')
