from django.contrib import admin
from .models import NotificationTemplate, NotificationLog, NotificationPreference


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'language', 'is_active')
    list_filter = ('template_type', 'language', 'is_active')
    search_fields = ('name', 'subject', 'body')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'event_type', 'status', 'created_at')
    list_filter = ('notification_type', 'event_type', 'status', 'created_at')
    search_fields = ('user__username', 'recipient_email', 'recipient_phone')
    date_hierarchy = 'created_at'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'sms_enabled', 'preferred_language')
    list_filter = ('email_enabled', 'sms_enabled', 'preferred_language')
    search_fields = ('user__username',)

