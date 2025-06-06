from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list view with essential information."""
    full_name = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'phone_number',
            'apartment_number', 'building_name', 'is_active',
            'is_approved', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed user view and updates."""
    full_name = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'phone_number',
            'apartment_number', 'building_name', 'address',
            'is_active', 'is_approved', 'is_staff', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'email', 'user_type', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def update(self, instance, validated_data):
        # Track if approval status is being changed
        if 'is_approved' in validated_data and validated_data['is_approved'] != instance.is_approved:
            instance._approval_status_changed = True
        
        return super().update(instance, validated_data)

class UserApprovalSerializer(serializers.ModelSerializer):
    """Serializer for user approval operations."""
    
    class Meta:
        model = User
        fields = ['id', 'is_approved']
        read_only_fields = ['id']
    
    def validate(self, attrs):
        # Prevent changing approval status of admin users
        if self.instance and self.instance.user_type == 'ADMIN':
            raise serializers.ValidationError("Cannot change approval status of admin users.")
        return attrs

class ResidentListSerializer(serializers.ModelSerializer):
    """Serializer for resident list (used in visitor registration)."""
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'apartment_number', 'building_name', 'phone_number'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_display_name(self, obj):
        """Return name with apartment info for better identification."""
        name = obj.get_full_name()
        if obj.apartment_number:
            name += f" (Apt. {obj.apartment_number}"
            if obj.building_name:
                name += f", {obj.building_name}"
            name += ")"
        return name

class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics."""
    total_users = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    active_residents = serializers.IntegerField()
    active_security = serializers.IntegerField()
    new_registrations_week = serializers.IntegerField()
    user_type_breakdown = serializers.DictField()

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates by the user themselves."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 
            'apartment_number', 'building_name', 'address'
        ]
    
    def validate(self, attrs):
        user = self.instance
        
        # Validate apartment_number for residents
        if user.user_type == 'RESIDENT':
            apartment_number = attrs.get('apartment_number', user.apartment_number)
            building_name = attrs.get('building_name', user.building_name)
            
            if not apartment_number:
                raise serializers.ValidationError("Apartment number is required for residents.")
            if not building_name:
                raise serializers.ValidationError("Building name is required for residents.")
        
        return attrs

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users (admin only)."""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'user_type', 'apartment_number', 'building_name',
            'address', 'password', 'is_active', 'is_approved'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate(self, attrs):
        # Validate apartment_number for residents
        if attrs.get('user_type') == 'RESIDENT':
            if not attrs.get('apartment_number'):
                raise serializers.ValidationError("Apartment number is required for residents.")
            if not attrs.get('building_name'):
                raise serializers.ValidationError("Building name is required for residents.")
        
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user