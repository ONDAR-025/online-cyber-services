"""
Notification-related Celery tasks.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import time
import logging

logger = logging.getLogger('notifications')


@shared_task(bind=True, max_retries=3)
def send_pending_notifications(self):
    """
    Send pending notifications, respecting quiet hours.
    Called every 15 minutes by Celery Beat.
    """
    from notifications.models import NotificationLog, NotificationPreference
    
    logger.info('Starting pending notification processing')
    
    now = timezone.now()
    current_time = now.time()
    
    # Get pending notifications
    pending_notifications = NotificationLog.objects.filter(
        status='pending',
        next_retry_at__lte=now
    ) | NotificationLog.objects.filter(
        status='queued'
    )
    
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    
    for notification in pending_notifications:
        try:
            # Check user notification preferences
            prefs, _ = NotificationPreference.objects.get_or_create(
                user=notification.user
            )
            
            # Check if notification type is enabled
            if notification.notification_type == 'email' and not prefs.email_enabled:
                notification.status = 'failed'
                notification.error_message = 'Email notifications disabled by user'
                notification.save()
                skipped_count += 1
                continue
            
            if notification.notification_type == 'sms' and not prefs.sms_enabled:
                notification.status = 'failed'
                notification.error_message = 'SMS notifications disabled by user'
                notification.save()
                skipped_count += 1
                continue
            
            # Check quiet hours
            if prefs.respect_quiet_hours and prefs.quiet_hours_start and prefs.quiet_hours_end:
                in_quiet_hours = False
                
                if prefs.quiet_hours_start < prefs.quiet_hours_end:
                    # Same day quiet hours (e.g., 22:00 to 07:00 next day)
                    in_quiet_hours = current_time >= prefs.quiet_hours_start or current_time <= prefs.quiet_hours_end
                else:
                    # Overnight quiet hours
                    in_quiet_hours = prefs.quiet_hours_start <= current_time <= time(23, 59, 59) or \
                                    time(0, 0, 0) <= current_time <= prefs.quiet_hours_end
                
                if in_quiet_hours:
                    logger.info(f'Skipping notification {notification.id} due to quiet hours')
                    skipped_count += 1
                    continue
            
            # Send notification based on type
            if notification.notification_type == 'email':
                send_email_notification(notification)
            elif notification.notification_type == 'sms':
                send_sms_notification(notification)
            
            sent_count += 1
            
        except Exception as e:
            failed_count += 1
            notification.retry_count += 1
            notification.error_message = str(e)
            
            if notification.can_retry():
                notification.status = 'failed'
                notification.next_retry_at = timezone.now() + timedelta(minutes=15 * notification.retry_count)
            else:
                notification.status = 'failed'
            
            notification.save()
            logger.error(f'Failed to send notification {notification.id}: {str(e)}')
    
    logger.info(f'Notification processing complete: {sent_count} sent, {failed_count} failed, {skipped_count} skipped')
    return {
        'sent': sent_count,
        'failed': failed_count,
        'skipped': skipped_count
    }


def send_email_notification(notification):
    """Send email via Azure Communication Services."""
    from azure.communication.email import EmailClient
    
    if not settings.ACS_CONNECTION_STRING:
        logger.warning('Azure Communication Services not configured')
        notification.status = 'failed'
        notification.error_message = 'ACS not configured'
        notification.save()
        return
    
    try:
        client = EmailClient.from_connection_string(settings.ACS_CONNECTION_STRING)
        
        message = {
            "senderAddress": settings.ACS_EMAIL_FROM,
            "recipients": {
                "to": [{"address": notification.recipient_email}],
            },
            "content": {
                "subject": notification.subject,
                "plainText": notification.body,
            }
        }
        
        poller = client.begin_send(message)
        result = poller.result()
        
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.acs_message_id = result.get('id', '')
        notification.save()
        
        logger.info(f'Email notification {notification.id} sent successfully')
        
    except Exception as e:
        logger.error(f'Failed to send email notification {notification.id}: {str(e)}')
        raise


def send_sms_notification(notification):
    """Send SMS via Azure Communication Services."""
    from azure.communication.sms import SmsClient
    
    if not settings.ACS_CONNECTION_STRING or not settings.ACS_SMS_FROM:
        logger.warning('Azure Communication Services SMS not configured')
        notification.status = 'failed'
        notification.error_message = 'ACS SMS not configured'
        notification.save()
        return
    
    try:
        client = SmsClient.from_connection_string(settings.ACS_CONNECTION_STRING)
        
        response = client.send(
            from_=settings.ACS_SMS_FROM,
            to=[notification.recipient_phone],
            message=notification.body
        )
        
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.acs_message_id = response.message_id if hasattr(response, 'message_id') else ''
        notification.save()
        
        logger.info(f'SMS notification {notification.id} sent successfully')
        
    except Exception as e:
        logger.error(f'Failed to send SMS notification {notification.id}: {str(e)}')
        raise


@shared_task(bind=True)
def send_dunning_notification(self, subscription_id, attempt_number):
    """
    Send dunning notification for failed subscription renewal.
    """
    from subscriptions.models import Subscription
    from notifications.models import NotificationLog, NotificationTemplate
    
    try:
        subscription = Subscription.objects.get(id=subscription_id)
        
        # Get template
        template = NotificationTemplate.objects.filter(
            name='dunning_reminder',
            template_type='email',
            is_active=True
        ).first()
        
        if not template:
            logger.warning('Dunning reminder template not found')
            return
        
        # Create notification
        subject = f'Payment Reminder for {subscription.product.name}'
        body = f'Your subscription renewal payment failed. Please update your payment method. Attempt {attempt_number}.'
        
        NotificationLog.objects.create(
            user=subscription.user,
            notification_type='email',
            event_type='dunning_reminder',
            recipient_email=subscription.user.email,
            subject=subject,
            body=body,
            template=template,
            subscription=subscription
        )
        
        logger.info(f'Dunning notification created for subscription {subscription_id}')
        
    except Exception as e:
        logger.error(f'Failed to create dunning notification: {str(e)}')


@shared_task(bind=True)
def send_admin_alert(self, subject, message):
    """Send alert to administrators."""
    logger.warning(f'ADMIN ALERT: {subject} - {message}')
    # In production, send actual email to admins
