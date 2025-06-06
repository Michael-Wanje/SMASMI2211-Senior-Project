from django.db import models
from django.contrib.auth import get_user_model
from apps.visitors.models import VisitRequest

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('visit_request', 'Visit Request'),
        ('visit_approved', 'Visit Approved'),
        ('visit_denied', 'Visit Denied'),
        ('visitor_arrival', 'Visitor Arrival'),
        ('visitor_blacklisted', 'Visitor Blacklisted'),
        ('security_alert', 'Security Alert'),
        ('resident_registration', 'Resident Registration'),
        ('system_update', 'System Update'),
    ]
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_notifications',
        null=True, 
        blank=True
    )
    notification_type = models.CharField(
        max_length=30, 
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    visit_request = models.ForeignKey(
        VisitRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'notifications'
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save()

class EmailLog(models.Model):
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('pending', 'Pending')
        ],
        default='pending'
    )
    error_message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
        db_table = 'email_logs'
    
    def __str__(self):
        return f"{self.subject} - {self.recipient_email} ({self.status})"