"""
Custom logging filters for the LMS.
"""
import logging
from django.utils.deprecation import MiddlewareMixin


class RequestIDFilter(logging.Filter):
    """
    Logging filter to add request ID to log records.
    """
    
    def filter(self, record):
        # Try to get request ID from thread-local storage
        from threading import current_thread
        thread = current_thread()
        request_id = getattr(thread, 'request_id', 'no-request-id')
        record.request_id = request_id
        return True
