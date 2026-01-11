"""
Celery configuration for LMS.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_config.settings')

app = Celery('lms')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Subscription renewals - check every hour
    'process-subscription-renewals': {
        'task': 'subscriptions.tasks.process_subscription_renewals',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Dunning schedule - process failed payments
    'process-dunning-schedule': {
        'task': 'subscriptions.tasks.process_dunning_schedule',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
    # Reconciliation - nightly at 2 AM
    'reconcile-payments': {
        'task': 'payments.tasks.reconcile_daily_payments',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    # Clean up expired payment intents
    'cleanup-expired-intents': {
        'task': 'payments.tasks.cleanup_expired_intents',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    # Send pending notifications
    'send-pending-notifications': {
        'task': 'notifications.tasks.send_pending_notifications',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
