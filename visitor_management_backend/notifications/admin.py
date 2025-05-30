from django.contrib import admin
from .models import Notification, NotificationTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'email_sent', 'created_at')
    list_filter = ('notification_type', 'is_read', 'email_sent', 'created_at')
    search_fields = ('title', 'recipient__email', 'message')
    readonly_fields = ('created_at',)

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_type', 'subject', 'is_active', 'created_at')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('template_type', 'subject')