"""
Notifications app models - Email and SMS notifications via Azure Communication Services.
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class NotificationTemplate(models.Model):
    """Templates for notifications in multiple languages."""
    
    TEMPLATE_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text='Template identifier, e.g., payment_success')
    template_type = models.CharField(max_length=10, choices=TEMPLATE_TYPE_CHOICES)
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    
    # Email specific
    subject = models.CharField(max_length=255, blank=True)
    
    # Content (supports template variables like {{user_name}}, {{amount}})
    body = models.TextField(help_text='Template body with variable placeholders')
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'template_type', 'language']
        ordering = ['name', 'language']
    
    def __str__(self):
        return f"{self.name} ({self.template_type} - {self.language})"


class NotificationLog(models.Model):
    """Log of all notifications sent."""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('subscription_renewed', 'Subscription Renewed'),
        ('subscription_renewal_failed', 'Subscription Renewal Failed'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('dunning_reminder', 'Dunning Reminder'),
        ('enrollment_confirmation', 'Enrollment Confirmation'),
        ('certificate_issued', 'Certificate Issued'),
        ('invoice_generated', 'Invoice Generated'),
        ('receipt_generated', 'Receipt Generated'),
        ('course_completion', 'Course Completion'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    
    # Recipient
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True, help_text='Format: +254712345678')
    
    # Content
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    
    # Template used
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Azure Communication Services Message ID
    acs_message_id = models.CharField(max_length=200, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    order = models.ForeignKey('commerce.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    subscription = models.ForeignKey('subscriptions.Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    invoice = models.ForeignKey('commerce.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.user.username} - {self.get_event_type_display()}"
    
    def can_retry(self):
        """Check if notification can be retried."""
        return self.status == 'failed' and self.retry_count < self.max_retries


class NotificationPreference(models.Model):
    """User preferences for notifications."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_payment_notifications = models.BooleanField(default=True)
    email_subscription_notifications = models.BooleanField(default=True)
    email_course_notifications = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    
    # SMS preferences
    sms_enabled = models.BooleanField(default=True)
    sms_payment_notifications = models.BooleanField(default=True)
    sms_subscription_notifications = models.BooleanField(default=True)
    sms_course_notifications = models.BooleanField(default=False)
    
    # Quiet hours (Kenya time)
    respect_quiet_hours = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text='e.g., 22:00')
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text='e.g., 07:00')
    
    # Language preference
    preferred_language = models.CharField(max_length=5, default='en', choices=[
        ('en', 'English'),
        ('sw', 'Swahili'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Preferences for {self.user.username}"

