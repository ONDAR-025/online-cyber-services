"""
Payments app models - Payment processing for M-Pesa, Airtel Money, and other providers.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
import json


class ProviderAccount(models.Model):
    """Provider credentials per tenant for M-Pesa, Airtel, etc."""
    
    PROVIDER_CHOICES = [
        ('mpesa', 'M-Pesa Daraja'),
        ('airtel', 'Airtel Money'),
        ('pesapal', 'Pesapal'),
        ('flutterwave', 'Flutterwave'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # Tenant identification (for multi-tenancy)
    tenant_name = models.CharField(max_length=100)
    
    # M-Pesa specific
    mpesa_consumer_key = models.CharField(max_length=200, blank=True)
    mpesa_consumer_secret = models.CharField(max_length=200, blank=True)
    mpesa_shortcode = models.CharField(max_length=20, blank=True)
    mpesa_passkey = models.CharField(max_length=200, blank=True)
    mpesa_environment = models.CharField(max_length=20, default='sandbox')  # sandbox or production
    
    # Airtel specific
    airtel_client_id = models.CharField(max_length=200, blank=True)
    airtel_client_secret = models.CharField(max_length=200, blank=True)
    airtel_environment = models.CharField(max_length=20, default='sandbox')
    
    # Azure Communication Services (email/SMS)
    acs_email_sender = models.EmailField(blank=True)
    acs_sms_sender = models.CharField(max_length=20, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tenant_name', 'provider']
        indexes = [
            models.Index(fields=['provider', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.tenant_name} - {self.get_provider_display()}"


class PaymentMethod(models.Model):
    """Stored payment methods for users."""
    
    METHOD_TYPE_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel', 'Airtel Money'),
        ('card_stub', 'Card (Stub)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES)
    
    # For mobile money
    phone_number = models.CharField(max_length=20, blank=True, help_text='Format: 254712345678')
    
    # For cards (stub only, not processing in v1)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        if self.phone_number:
            return f"{self.get_method_type_display()} - {self.phone_number}"
        return f"{self.get_method_type_display()}"


class PaymentIntent(models.Model):
    """Payment intent - represents an attempt to collect payment."""
    
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('requires_action', 'Requires Action'),  # e.g., waiting for STK push approval
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PROVIDER_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel', 'Airtel Money'),
        ('pesapal', 'Pesapal'),
        ('flutterwave', 'Flutterwave'),
    ]
    
    NEXT_ACTION_CHOICES = [
        ('stk_push', 'STK Push'),
        ('collect', 'Collect/USSD'),
        ('redirect', 'Redirect'),
        ('none', 'None'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('commerce.Order', on_delete=models.CASCADE, related_name='payment_intents')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_intents')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='KES')
    
    # Provider
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    next_action = models.CharField(max_length=20, choices=NEXT_ACTION_CHOICES, default='none')
    
    # Idempotency
    idempotency_key = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Provider-specific data (stored as JSON)
    provider_data = models.JSONField(default=dict, blank=True)
    
    # References
    provider_transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)  # M-Pesa specific
    merchant_request_id = models.CharField(max_length=100, blank=True)   # M-Pesa specific
    
    # Error handling
    error_message = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['checkout_request_id']),
        ]
    
    def __str__(self):
        return f"Payment Intent {self.id} - {self.status}"


class Payment(models.Model):
    """Completed payment record."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey('commerce.Order', on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='KES')
    
    # Provider details
    provider = models.CharField(max_length=20)
    provider_transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    provider_receipt_number = models.CharField(max_length=100, blank=True)  # M-Pesa receipt
    
    # Payer information
    payer_phone = models.CharField(max_length=20, blank=True)
    payer_name = models.CharField(max_length=100, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"Payment {self.provider_transaction_id} - KES {self.amount}"


class WebhookEvent(models.Model):
    """Store webhook events from payment providers for auditing and deduplication."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20)
    
    # Deduplication
    provider_event_id = models.CharField(max_length=200, unique=True, db_index=True, help_text='Unique ID from provider')
    
    # Event data
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    
    # Processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Linkage
    payment_intent = models.ForeignKey(PaymentIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Webhook {self.provider} - {self.event_type}"


class LedgerEntry(models.Model):
    """Double-entry ledger for financial reconciliation."""
    
    ENTRY_TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]
    
    ACCOUNT_CHOICES = [
        ('revenue', 'Revenue'),
        ('liability', 'Liability'),
        ('expense', 'Expense'),
        ('asset', 'Asset'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction reference
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='ledger_entries', null=True, blank=True)
    order = models.ForeignKey('commerce.Order', on_delete=models.CASCADE, related_name='ledger_entries', null=True, blank=True)
    refund = models.ForeignKey('commerce.Refund', on_delete=models.CASCADE, related_name='ledger_entries', null=True, blank=True)
    
    # Entry details
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='KES')
    
    # Description
    description = models.CharField(max_length=255)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Ledger entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.entry_type} - {self.account_type} - KES {self.amount}"

