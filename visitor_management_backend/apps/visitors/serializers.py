from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Visitor, VisitRequest, BlacklistedVisitor
from apps.users.models import CustomUser

User = get_user_model()

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ['id', 'name', 'phone_number', 'email', 'id_number', 'vehicle_registration', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_phone_number(self):
        phone = self.validated_data.get('phone_number')
        if phone and not phone.startswith('+'):
            raise serializers.ValidationError("Phone number must include country code (e.g., +254)")
        return phone

    def validate_id_number(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("ID number must be at least 6 characters long")
        return value

class VisitRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source='visitor.name', read_only=True)
    visitor_phone = serializers.CharField(source='visitor.phone_number', read_only=True)
    visitor_email = serializers.CharField(source='visitor.email', read_only=True)
    visitor_id_number = serializers.CharField(source='visitor.id_number', read_only=True)
    resident_name = serializers.CharField(source='resident.get_full_name', read_only=True)
    resident_apartment = serializers.CharField(source='resident.apartment_number', read_only=True)
    security_personnel_name = serializers.CharField(source='security_personnel.get_full_name', read_only=True)
    
    class Meta:
        model = VisitRequest
        fields = [
            'id', 'visitor', 'resident', 'purpose', 'visit_date', 'visit_time',
            'status', 'approval_date', 'security_personnel', 'entry_time',
            'exit_time', 'notes', 'created_at', 'updated_at',
            'visitor_name', 'visitor_phone', 'visitor_email', 'visitor_id_number',
            'resident_name', 'resident_apartment', 'security_personnel_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approval_date']

    def validate_visit_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Visit date cannot be in the past")
        return value

    def validate(self, data):
        # Check if visitor is blacklisted for this resident
        visitor = data.get('visitor')
        resident = data.get('resident')
        
        if visitor and resident:
            if BlacklistedVisitor.objects.filter(visitor=visitor, resident=resident).exists():
                raise serializers.ValidationError("This visitor is blacklisted and cannot book with this resident")
        
        return data

class VisitRequestCreateSerializer(serializers.ModelSerializer):
    visitor_data = VisitorSerializer(write_only=True)
    
    class Meta:
        model = VisitRequest
        fields = ['visitor_data', 'resident', 'purpose', 'visit_date', 'visit_time', 'notes']

    def create(self, validated_data):
        visitor_data = validated_data.pop('visitor_data')
        
        # Check if visitor already exists
        visitor, created = Visitor.objects.get_or_create(
            phone_number=visitor_data['phone_number'],
            defaults=visitor_data
        )
        
        # Create visit request
        visit_request = VisitRequest.objects.create(
            visitor=visitor,
            **validated_data
        )
        
        return visit_request

class VisitRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitRequest
        fields = ['status', 'notes', 'entry_time', 'exit_time', 'security_personnel']

    def update(self, instance, validated_data):
        from django.utils import timezone
        from apps.notifications.models import Notification
        
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Update the instance
        instance = super().update(instance, validated_data)
        
        # Handle status changes
        if old_status != new_status:
            if new_status == 'approved':
                instance.approval_date = timezone.now()
                instance.save()
                
                # Create notification for security
                security_users = CustomUser.objects.filter(user_type='security', is_active=True)
                for security_user in security_users:
                    Notification.objects.create(
                        user=security_user,
                        title='Visit Request Approved',
                        message=f'Visit request for {instance.visitor.name} to {instance.resident.get_full_name()} has been approved.',
                        notification_type='visit_approved'
                    )
                    
            elif new_status == 'denied':
                # Blacklist visitor for this resident
                BlacklistedVisitor.objects.get_or_create(
                    visitor=instance.visitor,
                    resident=instance.resident,
                    defaults={'reason': 'Visit request denied'}
                )
        
        return instance

class BlacklistedVisitorSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source='visitor.name', read_only=True)
    visitor_phone = serializers.CharField(source='visitor.phone_number', read_only=True)
    resident_name = serializers.CharField(source='resident.get_full_name', read_only=True)
    
    class Meta:
        model = BlacklistedVisitor
        fields = [
            'id', 'visitor', 'resident', 'reason', 'blacklisted_at',
            'visitor_name', 'visitor_phone', 'resident_name'
        ]
        read_only_fields = ['id', 'blacklisted_at']