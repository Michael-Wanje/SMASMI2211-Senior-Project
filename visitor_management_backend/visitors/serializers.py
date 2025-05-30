from rest_framework import serializers
from django.utils import timezone
from residents.serializers import ResidentSerializer
from authentication.serializers import UserSerializer
from .models import Visitor, VisitorLog

class VisitorLogSerializer(serializers.ModelSerializer):
    performed_by = UserSerializer(read_only=True)

    class Meta:
        model = VisitorLog
        fields = '__all__'

class VisitorSerializer(serializers.ModelSerializer):
    resident_info = ResidentSerializer(source='resident', read_only=True)
    approved_by_info = UserSerializer(source='approved_by', read_only=True)
    checked_in_by_info = UserSerializer(source='checked_in_by', read_only=True)
    created_by_info = UserSerializer(source='created_by', read_only=True)
    logs = VisitorLogSerializer(many=True, read_only=True)
    can_check_in = serializers.BooleanField(read_only=True)
    can_check_out = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Visitor
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 
                           'approved_by', 'approved_at', 'checked_in_at', 
                           'checked_out_at', 'checked_in_by')

class VisitorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ('full_name', 'phone_number', 'email', 'id_number', 'company',
                 'resident', 'purpose', 'visit_date', 'visit_time', 
                 'expected_duration', 'number_of_visitors', 'additional_notes')

    def validate_visit_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Visit date cannot be in the past")
        return value

    def create(self, validated_data):
        visitor = Visitor.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        
        # Create log entry
        VisitorLog.objects.create(
            visitor=visitor,
            action='created',
            performed_by=self.context['request'].user,
            notes=f"Visitor registration created"
        )
        
        return visitor

class VisitorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ('full_name', 'phone_number', 'email', 'id_number', 'company',
                 'purpose', 'visit_date', 'visit_time', 'expected_duration', 
                 'number_of_visitors', 'additional_notes')

    def validate_visit_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Visit date cannot be in the past")
        return value

class VisitorApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'deny'])
    notes = serializers.CharField(required=False, allow_blank=True)

class VisitorCheckInOutSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)