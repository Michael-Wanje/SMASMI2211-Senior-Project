from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
from .models import Visitor, VisitorLog
from .serializers import (VisitorSerializer, VisitorCreateSerializer, 
                         VisitorUpdateSerializer, VisitorApprovalSerializer,
                         VisitorCheckInOutSerializer, VisitorLogSerializer)
from notifications.utils import send_visitor_notification

class VisitorListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Visitor.objects.all().select_related(
            'resident__user', 'approved_by', 'checked_in_by', 'created_by'
        ).prefetch_related('logs')
        
        # Filter by user type
        if self.request.user.user_type == 'resident':
            queryset = queryset.filter(resident__user=self.request.user)
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        date_filter = self.request.GET.get('date')
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(visit_date=filter_date)
            except ValueError:
                pass
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VisitorCreateSerializer
        return VisitorSerializer

    def perform_create(self, serializer):
        visitor = serializer.save()
        
        # Send notification to resident
        send_visitor_notification(
            visitor=visitor,
            notification_type='new_visitor_request',
            recipient=visitor.resident.user
        )

class VisitorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Visitor.objects.all().select_related(
        'resident__user', 'approved_by', 'checked_in_by', 'created_by'
    ).prefetch_related('logs')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return VisitorUpdateSerializer
        return VisitorSerializer

    def perform_update(self, serializer):
        visitor = serializer.save()
        
        # Create log entry
        VisitorLog.objects.create(
            visitor=visitor,
            action='updated',
            performed_by=self.request.user,
            notes='Visitor information updated'
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_visitor(request, pk):
    visitor = get_object_or_404(Visitor, pk=pk)
    
    # Check permissions
    if (request.user.user_type not in ['admin', 'security'] and 
        visitor.resident.user != request.user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = VisitorApprovalSerializer(data=request.data)
    if serializer.is_valid():
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        if action == 'approve':
            visitor.status = 'approved'
            visitor.approved_by = request.user
            visitor.approved_at = timezone.now()
            log_action = 'approved'
            message = 'Visitor approved successfully'
            notification_type = 'visitor_approved'
        else:
            visitor.status = 'denied'
            visitor.approved_by = request.user
            visitor.approved_at = timezone.now()
            log_action = 'denied'
            message = 'Visitor denied'
            notification_type = 'visitor_denied'
        
        visitor.save()
        
        # Create log entry
        VisitorLog.objects.create(
            visitor=visitor,
            action=log_action,
            performed_by=request.user,
            notes=notes
        )
        
        # Send notification
        send_visitor_notification(
            visitor=visitor,
            notification_type=notification_type,
            recipient=visitor.created_by
        )
        
        return Response({
            'message': message,
            'visitor': VisitorSerializer(visitor).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_in_visitor(request, pk):
    visitor = get_object_or_404(Visitor, pk=pk)
    
    # Check if user has permission (security or admin)
    if request.user.user_type not in ['admin', 'security']:
        return Response(
            {'error': 'Only security personnel can check in visitors'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not visitor.can_check_in:
        return Response(
            {'error': 'Visitor cannot be checked in'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = VisitorCheckInOutSerializer(data=request.data)
    if serializer.is_valid():
        visitor.status = 'checked_in'
        visitor.checked_in_at = timezone.now()
        visitor.checked_in_by = request.user
        visitor.save()
        
        # Create log entry
        VisitorLog.objects.create(
            visitor=visitor,
            action='checked_in',
            performed_by=request.user,
            notes=serializer.validated_data.get('notes', '')
        )
        
        # Send notification to resident
        send_visitor_notification(
            visitor=visitor,
            notification_type='visitor_checked_in',
            recipient=visitor.resident.user
        )
        
        return Response({
            'message': 'Visitor checked in successfully',
            'visitor': VisitorSerializer(visitor).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_out_visitor(request, pk):
    visitor = get_object_or_404(Visitor, pk=pk)
    
    # Check if user has permission (security or admin)
    if request.user.user_type not in ['admin', 'security']:
        return Response(
            {'error': 'Only security personnel can check out visitors'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not visitor.can_check_out:
        return Response(
            {'error': 'Visitor cannot be checked out'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = VisitorCheckInOutSerializer(data=request.data)
    if serializer.is_valid():
        visitor.status = 'checked_out'
        visitor.checked_out_at = timezone.now()
        visitor.save()
        
        # Create log entry
        VisitorLog.objects.create(
            visitor=visitor,
            action='checked_out',
            performed_by=request.user,
            notes=serializer.validated_data.get('notes', '')
        )
        
        # Send notification to resident
        send_visitor_notification(
            visitor=visitor,
            notification_type='visitor_checked_out',
            recipient=visitor.resident.user
        )
        
        return Response({
            'message': 'Visitor checked out successfully',
            'visitor': VisitorSerializer(visitor).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def visitor_stats(request):
    today = timezone.now().date()
    
    # Base queryset
    queryset = Visitor.objects.all()
    if request.user.user_type == 'resident':
        queryset = queryset.filter(resident__user=request.user)
    
    stats = {
        'total_visitors': queryset.count(),
        'pending_approvals': queryset.filter(status='pending').count(),
        'approved_visitors': queryset.filter(status='approved').count(),
        'checked_in_today': queryset.filter(
            status='checked_in', 
            checked_in_at__date=today
        ).count(),
        'visitors_today': queryset.filter(visit_date=today).count(),
    }
    
    # Recent activity
    recent_visitors = queryset.order_by('-created_at')[:5]
    stats['recent_visitors'] = VisitorSerializer(recent_visitors, many=True).data
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_data(request):
    today = timezone.now().date()
    
    # Base queryset
    queryset = Visitor.objects.all()
    if request.user.user_type == 'resident':
        queryset = queryset.filter(resident__user=request.user)
    
    # Today's visitors
    todays_visitors = queryset.filter(visit_date=today)
    
    # Pending approvals
    pending_visitors = queryset.filter(status='pending')
    
    # Recent activity (last 7 days)
    week_ago = today - timedelta(days=7)
    recent_activity = queryset.filter(created_at__date__gte=week_ago)
    
    data = {
        'todays_visitors': {
            'total': todays_visitors.count(),
            'checked_in': todays_visitors.filter(status='checked_in').count(),
            'pending': todays_visitors.filter(status='pending').count(),
            'visitors': VisitorSerializer(todays_visitors.order_by('-visit_time'), many=True).data
        },
        'pending_approvals': {
            'count': pending_visitors.count(),
            'visitors': VisitorSerializer(pending_visitors.order_by('-created_at'), many=True).data
        },
        'recent_activity': {
            'count': recent_activity.count(),
            'visitors': VisitorSerializer(recent_activity.order_by('-created_at')[:10], many=True).data
        }
    }
    
    return Response(data)