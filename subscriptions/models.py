"""
Subscriptions app models - Recurring billing with dunning support.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from datetime import timedelta
from django.utils import timezone


class Subscription(models.Model):
    """Subscription model for recurring billing."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('cancelled', 'Cancelled'),
        ('incomplete', 'Incomplete'),
        ('trialing', 'Trialing'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    product = models.ForeignKey('commerce.Product', on_delete=models.PROTECT, related_name='subscriptions')
    price = models.ForeignKey('commerce.Price', on_delete=models.PROTECT, related_name='subscriptions')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')
    
    # Billing cycle
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    billing_anchor = models.DateTimeField(help_text='Day of month/year to bill on')
    
    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Trial period
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # Dunning - grace period until access is revoked
    grace_until = models.DateTimeField(null=True, blank=True)
    
    # Latest invoice for this subscription
    latest_invoice = models.ForeignKey('commerce.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscription_latest')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'current_period_end']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.status})"
    
    def is_in_trial(self):
        """Check if subscription is in trial period."""
        if self.trial_end:
            return timezone.now() < self.trial_end
        return False
    
    def needs_renewal(self):
        """Check if subscription needs renewal."""
        return timezone.now() >= self.current_period_end and self.status == 'active'


class SubscriptionItem(models.Model):
    """Line items in a subscription (for future multi-item subscriptions)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='items')
    
    product = models.ForeignKey('commerce.Product', on_delete=models.PROTECT)
    price = models.ForeignKey('commerce.Price', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.product.name} x {self.quantity}"


class SubscriptionRenewalAttempt(models.Model):
    """Track renewal attempts and dunning schedule."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='renewal_attempts')
    
    # Attempt details
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment
    payment_intent = models.ForeignKey('payments.PaymentIntent', on_delete=models.SET_NULL, null=True, blank=True, related_name='renewal_attempts')
    order = models.ForeignKey('commerce.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='renewal_attempts')
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    # Timing
    scheduled_at = models.DateTimeField(help_text='When this attempt should be made')
    attempted_at = models.DateTimeField(null=True, blank=True)
    succeeded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"Renewal Attempt {self.attempt_number} for {self.subscription}"


class DunningSchedule(models.Model):
    """Dunning configuration for handling failed payments."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    
    # Schedule in days after failure: [0, 1, 3, 7]
    retry_schedule = models.JSONField(help_text='List of days after failure to retry, e.g., [0, 1, 3, 7]')
    
    # Grace period before downgrading/cancelling
    grace_period_days = models.PositiveIntegerField(default=7)
    
    # Actions after grace period
    cancel_subscription = models.BooleanField(default=False, help_text='Cancel subscription after grace period')
    downgrade_to_free = models.BooleanField(default=True, help_text='Downgrade to free tier')
    
    # Notifications
    send_email_notifications = models.BooleanField(default=True)
    send_sms_notifications = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name
    
    def get_retry_days(self):
        """Get the retry schedule as a list."""
        if isinstance(self.retry_schedule, list):
            return self.retry_schedule
        return [0, 1, 3, 7]  # Default schedule


class SubscriptionUsage(models.Model):
    """Track usage for metered billing (future enhancement)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='usage_records')
    subscription_item = models.ForeignKey(SubscriptionItem, on_delete=models.CASCADE, related_name='usage_records')
    
    # Usage
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Metadata
    description = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.subscription} - {self.quantity} units"

