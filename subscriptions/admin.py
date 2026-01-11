from django.contrib import admin
from .models import Subscription, SubscriptionItem, SubscriptionRenewalAttempt, DunningSchedule


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'status', 'current_period_start', 'current_period_end')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'product__name')
    date_hierarchy = 'created_at'


@admin.register(SubscriptionRenewalAttempt)
class SubscriptionRenewalAttemptAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'attempt_number', 'status', 'scheduled_at')
    list_filter = ('status', 'scheduled_at')
    search_fields = ('subscription__user__username',)


@admin.register(DunningSchedule)
class DunningScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'grace_period_days', 'is_active', 'is_default')
    list_filter = ('is_active', 'is_default')

