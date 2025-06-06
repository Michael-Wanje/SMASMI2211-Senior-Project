from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from .models import Notification
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationUpdateSerializer, BulkNotificationSerializer
)
from .tasks import send_email_notification

User = get_user_model()

class NotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated user
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Notification.objects.filter(user=user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            is_read = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset.order_by('-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a notification
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return NotificationUpdateSerializer
        return NotificationSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, pk):
    """
    Mark a specific notification as read
    """
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read(request):
    """
    Mark all notifications as read for the authenticated user
    """
    updated_count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({
        'message': f'{updated_count} notifications marked as read',
        'updated_count': updated_count
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_counts(request):
    """
    Get notification counts for the authenticated user
    """
    user = request.user
    
    total_count = Notification.objects.filter(user=user).count()
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    
    # Count by type
    type_counts = {}
    for notification_type, _ in Notification.NOTIFICATION_TYPES:
        count = Notification.objects.filter(
            user=user, 
            notification_type=notification_type,
            is_read=False
        ).count()
        type_counts[notification_type] = count
    
    return Response({
        'total_count': total_count,
        'unread_count': unread_count,
        'type_counts': type_counts
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_notification(request):
    """
    Create a new notification (Admin only)
    """
    if request.user.user_type != 'admin':
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = NotificationCreateSerializer(data=request.data)
    if serializer.is_valid():
        notification = serializer.save()
        
        # Send email notification if enabled
        send_email_notification.delay(notification.id)
        
        response_serializer = NotificationSerializer(notification)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_bulk_notification(request):
    """
    Send bulk notifications (Admin only)
    """
    if request.user.user_type != 'admin':
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = BulkNotificationSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        user_type = data['user_type']
        
        # Get target users
        if user_type == 'all':
            users = User.objects.filter(is_active=True)
        else:
            users = User.objects.filter(user_type=user_type, is_active=True)
        
        # Create notifications for all target users
        notifications = []
        for user in users:
            notification = Notification(
                user=user,
                title=data['title'],
                message=data['message'],
                notification_type=data['notification_type']
            )
            notifications.append(notification)
        
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send email notifications
        for notification in created_notifications:
            send_email_notification.delay(notification.id)
        
        return Response({
            'message': f'{len(created_notifications)} notifications sent successfully',
            'count': len(created_notifications)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_read_notifications(request):
    """
    Delete all read notifications for the authenticated user
    """
    deleted_count = Notification.objects.filter(
        user=request.user, 
        is_read=True
    ).delete()[0]
    
    return Response({
        'message': f'{deleted_count} read notifications deleted',
        'deleted_count': deleted_count
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_notifications(request):
    """
    Get recent notifications for the authenticated user (last 10)
    """
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)