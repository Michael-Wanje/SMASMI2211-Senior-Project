from django.db import models
from authentication.models import User

class Resident(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resident_profile')
    apartment_number = models.CharField(max_length=20)
    block = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    move_in_date = models.DateField()
    is_owner = models.BooleanField(default=True)
    additional_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['apartment_number', 'block']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.apartment_number}"

class ResidentContact(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50)
    is_emergency_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.resident.user.get_full_name()}"