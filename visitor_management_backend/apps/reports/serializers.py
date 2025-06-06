from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta

class ReportFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    resident_id = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(
        choices=['pending', 'approved', 'denied', 'all'],
        default='all',
        required=False
    )
    
    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date must be before end date")
        
        # Default to last 30 days if no dates provided
        if not start_date and not end_date:
            data['end_date'] = timezone.now().date()
            data['start_date'] = data['end_date'] - timedelta(days=30)
        elif not start_date:
            data['start_date'] = end_date - timedelta(days=30)
        elif not end_date:
            data['end_date'] = timezone.now().date()
        
        return data

class VisitorReportSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    visitor_name = serializers.CharField()
    visitor_phone = serializers.CharField()
    visitor_email = serializers.CharField()
    resident_name = serializers.CharField()
    resident_apartment = serializers.CharField()
    purpose = serializers.CharField()
    visit_date = serializers.DateField()
    visit_time = serializers.TimeField()
    status = serializers.CharField()
    entry_time = serializers.DateTimeField()
    exit_time = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    security_personnel = serializers.CharField()
    created_at = serializers.DateTimeField()

class DailyReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    denied_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    total_entries = serializers.IntegerField()
    unique_visitors = serializers.IntegerField()

class ResidentReportSerializer(serializers.Serializer):
    resident_id = serializers.IntegerField()
    resident_name = serializers.CharField()
    apartment_number = serializers.CharField()
    total_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    denied_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    unique_visitors = serializers.IntegerField()
    last_visit_date = serializers.DateField()

class SecurityReportSerializer(serializers.Serializer):
    security_personnel_id = serializers.IntegerField()
    security_personnel_name = serializers.CharField()
    total_entries_processed = serializers.IntegerField()
    total_exits_processed = serializers.IntegerField()
    walk_in_visitors = serializers.IntegerField()
    active_days = serializers.IntegerField()

class VisitorFrequencySerializer(serializers.Serializer):
    visitor_name = serializers.CharField()
    visitor_phone = serializers.CharField()
    visitor_email = serializers.CharField()
    total_visits = serializers.IntegerField()
    approved_visits = serializers.IntegerField()
    denied_visits = serializers.IntegerField()
    unique_residents = serializers.IntegerField()
    last_visit_date = serializers.DateField()
    first_visit_date = serializers.DateField()

class MonthlyStatsSerializer(serializers.Serializer):
    month = serializers.CharField()
    year = serializers.IntegerField()
    total_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    denied_requests = serializers.IntegerField()
    unique_visitors = serializers.IntegerField()
    unique_residents = serializers.IntegerField()
    average_daily_requests = serializers.FloatField()

class BlacklistReportSerializer(serializers.Serializer):
    visitor_name = serializers.CharField()
    visitor_phone = serializers.CharField()
    visitor_email = serializers.CharField()
    resident_name = serializers.CharField()
    resident_apartment = serializers.CharField()
    reason = serializers.CharField()
    blacklisted_at = serializers.DateTimeField()
    total_denied_requests = serializers.IntegerField()