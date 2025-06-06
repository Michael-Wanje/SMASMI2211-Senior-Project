from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class PasswordResetRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_requests')
    token = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'password_reset_requests'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Password reset for {self.user.email}"

class LoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    is_successful = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'login_attempts'
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "Success" if self.is_successful else "Failed"
        return f"{self.email} - {status} at {self.timestamp}"