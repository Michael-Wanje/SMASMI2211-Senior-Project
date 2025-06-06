from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid

class User(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('resident', 'Resident'),
        ('security', 'Security'),
        ('visitor', 'Visitor'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True
    )
    is_approved = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'user_type']
    
    class Meta:
        db_table = 'users'
        
    def __str__(self):
        return f"{self.email} - {self.user_type}"
    
    def save(self, *args, **kwargs):
        # Auto-approve admin and security users
        if self.user_type in ['admin', 'security']:
            self.is_approved = True
        super().save(*args, **kwargs)

class Resident(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resident_profile')
    apartment_number = models.CharField(max_length=20)
    building = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    is_primary = models.BooleanField(default=True)
    move_in_date = models.DateField(blank=True, null=True)
    
    class Meta:
        db_table = 'residents'
        unique_together = ['apartment_number', 'building']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Apt {self.apartment_number}"

class SecurityPersonnel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'security_personnel'
        verbose_name_plural = 'Security Personnel'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"