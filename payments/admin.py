from django.contrib import admin
from .models import (
    ProviderAccount, PaymentMethod, PaymentIntent, Payment,
    WebhookEvent, LedgerEntry
)


@admin.register(ProviderAccount)
class ProviderAccountAdmin(admin.ModelAdmin):
    list_display = ('tenant_name', 'provider', 'is_active', 'created_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('tenant_name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'phone_number', 'is_default', 'is_active')
    list_filter = ('method_type', 'is_default', 'is_active')
    search_fields = ('user__username', 'phone_number')


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'provider', 'status', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('user__username', 'id', 'provider_transaction_id')
    date_hierarchy = 'created_at'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('provider_transaction_id', 'user', 'amount', 'provider', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('user__username', 'provider_transaction_id', 'provider_receipt_number')
    date_hierarchy = 'created_at'


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('provider', 'event_type', 'status', 'created_at')
    list_filter = ('provider', 'status', 'event_type', 'created_at')
    search_fields = ('provider_event_id',)
    date_hierarchy = 'created_at'


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_type', 'account_type', 'amount', 'description', 'created_at')
    list_filter = ('entry_type', 'account_type', 'created_at')
    date_hierarchy = 'created_at'

