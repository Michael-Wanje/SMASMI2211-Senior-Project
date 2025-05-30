from django.db import models
from authentication.models import User
from residents.models import Resident

class Visitor(models.Model):
    VISIT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('expired', 'Expired'),
    )

    VISIT_PURPOSE_CHOICES = (
        ('personal', 'Personal Visit'),
        ('business', 'Business'),
        ('delivery', 'Delivery'),
        ('maintenance', 'Maintenance'),
        ('emergency', 'Emergency'),
        ('other', 'Other'),
    )

    # Visitor Information
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=100, blank=True)
    
    # Visit Details
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='visitors')
    purpose = models.CharField(max_length=20, choices=VISIT_PURPOSE_CHOICES, default='personal')
    visit_date = models.DateField()
    visit_time = models.TimeField()
    expected_duration = models.DurationField(help_text="Expected duration of visit")
    number_of_visitors = models.PositiveIntegerField(default=1)
    additional_notes = models.TextField(blank=True)
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=VISIT_STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_visits')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Check-in/Check-out
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_visits')
    
    # System fields
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_visits')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} visiting {self.resident.user.get_full_name()}"

    @property
    def is_active(self):
        return self.status in ['approved', 'checked_in']

    @property
    def can_check_in(self):
        return self.status == 'approved'

    @property
    def can_check_out(self):
        return self.status == 'checked_in'

class VisitorLog(models.Model):
    ACTION_CHOICES = (
        ('created', 'Created'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('updated', 'Updated'),
    )

    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.visitor.full_name}"