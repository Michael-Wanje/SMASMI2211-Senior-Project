from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.users.models import Resident, SecurityPersonnel
from .models import PasswordResetRequest
import secrets
import string

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    # Resident specific fields
    apartment_number = serializers.CharField(required=False, allow_blank=True)
    building = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)
    
    # Security specific fields
    employee_id = serializers.CharField(required=False, allow_blank=True)
    shift_start = serializers.TimeField(required=False)
    shift_end = serializers.TimeField(required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'phone_number',
            'user_type', 'password', 'password_confirm', 'apartment_number',
            'building', 'emergency_contact', 'employee_id', 'shift_start', 'shift_end'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate resident fields
        if attrs['user_type'] == 'resident':
            if not attrs.get('apartment_number'):
                raise serializers.ValidationError("Apartment number is required for residents")
        
        # Validate security fields
        if attrs['user_type'] == 'security':
            if not attrs.get('employee_id'):
                raise serializers.ValidationError("Employee ID is required for security personnel")
            if not attrs.get('shift_start') or not attrs.get('shift_end'):
                raise serializers.ValidationError("Shift times are required for security personnel")
        
        return attrs
    
    def create(self, validated_data):
        # Remove password_confirm and profile-specific fields
        password_confirm = validated_data.pop('password_confirm')
        apartment_number = validated_data.pop('apartment_number', None)
        building = validated_data.pop('building', None)
        emergency_contact = validated_data.pop('emergency_contact', None)
        employee_id = validated_data.pop('employee_id', None)
        shift_start = validated_data.pop('shift_start', None)
        shift_end = validated_data.pop('shift_end', None)
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Create profile based on user type
        if user.user_type == 'resident':
            Resident.objects.create(
                user=user,
                apartment_number=apartment_number,
                building=building or '',
                emergency_contact=emergency_contact or ''
            )
        elif user.user_type == 'security':
            SecurityPersonnel.objects.create(
                user=user,
                employee_id=employee_id,
                shift_start=shift_start,
                shift_end=shift_end
            )
        
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            
            if not user.is_approved and user.user_type == 'resident':
                raise serializers.ValidationError('Account pending approval')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Email and password required')

class UserProfileSerializer(serializers.ModelSerializer):
    resident_profile = serializers.SerializerMethodField()
    security_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'user_type', 'is_approved', 'profile_picture',
            'created_at', 'resident_profile', 'security_profile'
        ]
        read_only_fields = ['id', 'email', 'user_type', 'is_approved', 'created_at']
    
    def get_resident_profile(self, obj):
        if hasattr(obj, 'resident_profile'):
            return {
                'apartment_number': obj.resident_profile.apartment_number,
                'building': obj.resident_profile.building,
                'emergency_contact': obj.resident_profile.emergency_contact,
                'move_in_date': obj.resident_profile.move_in_date
            }
        return None
    
    def get_security_profile(self, obj):
        if hasattr(obj, 'security_profile'):
            return {
                'employee_id': obj.security_profile.employee_id,
                'shift_start': obj.security_profile.shift_start,
                'shift_end': obj.security_profile.shift_end,
                'is_active': obj.security_profile.is_active
            }
        return None

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        try:
            reset_request = PasswordResetRequest.objects.get(
                token=attrs['token'],
                is_used=False
            )
            if reset_request.is_expired():
                raise serializers.ValidationError("Reset token has expired")
            
            attrs['reset_request'] = reset_request
        except PasswordResetRequest.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token")
        
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs