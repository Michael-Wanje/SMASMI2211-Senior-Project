from django.db import models
from django.core.validators import RegexValidator
from apps.users.models import User, Resident
import uuid

class Visitor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    id_number = models.CharField(max_length=20, unique=True)
    vehicle_plate = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='visitor_photos/', blank=True, null=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'visitors'
    
    def __str__(self):
        return f"{self.full_name} - {self.id_number}"

class VisitRequest(models.Model):
    REQUEST_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    VISIT_TYPES = (
        ('personal', 'Personal Visit'),
        ('delivery', 'Delivery'),
        ('service', 'Service Provider'),
        ('business', 'Business Meeting'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visit_requests')
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='visitor_requests')
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPES, default='personal')
    purpose = models.TextField()
    expected_date = models.DateField()
    expected_time = models.TimeField()
    status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='pending')
    qr_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Response fields
    response_date = models.DateTimeField(blank=True, null=True)
    response_notes = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responded_requests')
    
    # Pre-approved visits (registered by resident)
    is_pre_approved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'visit_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.visitor.full_name} -> {self.resident.user.get_full_name()} ({self.status})"

class VisitLog(models.Model):
    LOG_TYPES = (
        ('entry', 'Entry'),
        ('exit', 'Exit'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit_request = models.ForeignKey(VisitRequest, on_delete=models.CASCADE, related_name='logs', blank=True, null=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='logs')
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='visitor_logs')
    security_personnel = models.ForeignKey('users.SecurityPersonnel', on_delete=models.CASCADE, related_name='recorded_logs')
    
    log_type = models.CharField(max_length=10, choices=LOG_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    # For walk-in visitors
    is_walk_in = models.BooleanField(default=False)
    walk_in_approved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'visit_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.visitor.full_name} - {self.log_type} at {self.timestamp}"

class BlacklistedVisitor(models.Model):
    visitor = models.OneToOneField(Visitor, on_delete=models.CASCADE, related_name='blacklist_record')
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='blacklisted_visitors')
    blacklisted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklisted_visitors')
    reason = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'blacklisted_visitors'
        unique_together = ['visitor', 'resident']
    
    def __str__(self):
        return f"{self.visitor.full_name} blacklisted by {self.resident.user.get_full_name()}"