from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'notification_type',
            'is_read', 'read_at', 'created_at', 'user_name'
        ]
        read_only_fields = ['id', 'created_at', 'user_name']

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['user', 'title', 'message', 'notification_type']

class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['is_read']
        
    def update(self, instance, validated_data):
        from django.utils import timezone
        
        if validated_data.get('is_read', False) and not instance.is_read:
            instance.read_at = timezone.now()
        elif not validated_data.get('is_read', True) and instance.is_read:
            instance.read_at = None
            
        instance.is_read = validated_data.get('is_read', instance.is_read)
        instance.save()
        return instance

class BulkNotificationSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(
        choices=['resident', 'security', 'admin', 'all'],
        default='all'
    )
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=[
            ('general', 'General'),
            ('visit_request', 'Visit Request'),
            ('visit_approved', 'Visit Approved'),
            ('visit_denied', 'Visit Denied'),
            ('walk_in_visitor', 'Walk-in Visitor'),
            ('security_alert', 'Security Alert'),
            ('system_announcement', 'System Announcement'),
        ],
        default='general'
    )