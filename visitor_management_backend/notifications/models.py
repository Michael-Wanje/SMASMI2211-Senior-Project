from django.db import models
from authentication.models import User

class NotificationTemplate(models.Model):
    TEMPLATE_TYPES = (
        ('new_visitor_request', 'New Visitor Request'),
        ('visitor_approved', 'Visitor Approved'),
        ('visitor_denied', 'Visitor Denied'),
        ('visitor_checked_in', 'Visitor Checked In'),
        ('visitor_checked_out', 'Visitor Checked Out'),
        ('security_alert', 'Security Alert'),
    )
    
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=200)
    email_body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_template_type_display()} - {self.subject}"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.recipient.email}"