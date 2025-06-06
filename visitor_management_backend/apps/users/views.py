from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    UserListSerializer, UserDetailSerializer, UserApprovalSerializer,
    UserStatsSerializer, ResidentListSerializer
)
from apps.authentication.permissions import IsAdminUser, IsApprovedUser
from utils.permissions import IsAdminOrResident

User = get_user_model()

class UserListCreateView(generics.ListCreateAPIView):
    """
    List all users or create a new user (Admin only).
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        user_type = self.request.query_params.get('user_type', None)
        is_approved = self.request.query_params.get('is_approved', None)
        search = self.request.query_params.get('search', None)
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        if is_approved is not None:
            is_approved_bool = is_approved.lower() == 'true'
            queryset = queryset.filter(is_approved=is_approved_bool)
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(apartment_number__icontains=search)
            )
        
        return queryset

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a user instance (Admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Prevent deletion of superusers
        if user.is_superuser:
            return Response(
                {'error': 'Cannot delete superuser account'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent self-deletion
        if user == request.user:
            return Response(
                {'error': 'Cannot delete your own account'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)

class UserApprovalView(generics.UpdateAPIView):
    """
    Approve or disapprove a user (Admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserApprovalSerializer
    permission_classes = [IsAdminUser]
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Prevent changing approval status of admin users
        if user.user_type == 'ADMIN':
            return Response(
                {'error': 'Cannot change approval status of admin users'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set flag to trigger notification signal
        user._approval_status_changed = True
        
        return super().update(request, *args, **kwargs)

class ResidentListView(generics.ListAPIView):
    """
    List all approved residents (for visitor registration).
    """
    serializer_class = ResidentListSerializer
    permission_classes = [IsApprovedUser]
    
    def get_queryset(self):
        return User.objects.filter(
            user_type='RESIDENT',
            is_approved=True,
            is_active=True
        ).order_by('first_name', 'last_name')

@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_stats(request):
    """
    Get user statistics for admin dashboard.
    """
    total_users = User.objects.count()
    pending_approvals = User.objects.filter(is_approved=False).exclude(user_type='ADMIN').count()
    active_residents = User.objects.filter(user_type='RESIDENT', is_active=True, is_approved=True).count()
    active_security = User.objects.filter(user_type='SECURITY', is_active=True, is_approved=True).count()
    
    # New registrations in last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    new_registrations = User.objects.filter(date_joined__gte=week_ago).count()
    
    stats = {
        'total_users': total_users,
        'pending_approvals': pending_approvals,
        'active_residents': active_residents,
        'active_security': active_security,
        'new_registrations_week': new_registrations,
        'user_type_breakdown': {
            'residents': User.objects.filter(user_type='RESIDENT').count(),
            'security': User.objects.filter(user_type='SECURITY').count(),
            'admins': User.objects.filter(user_type='ADMIN').count(),
        }
    }
    
    serializer = UserStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_approve_users(request):
    """
    Bulk approve multiple users.
    """
    user_ids = request.data.get('user_ids', [])
    
    if not user_ids:
        return Response(
            {'error': 'No user IDs provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    users = User.objects.filter(
        id__in=user_ids,
        is_approved=False
    ).exclude(user_type='ADMIN')
    
    updated_count = 0
    for user in users:
        user.is_approved = True
        user._approval_status_changed = True
        user.save()
        updated_count += 1
    
    return Response({
        'message': f'{updated_count} users approved successfully',
        'approved_count': updated_count
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_disapprove_users(request):
    """
    Bulk disapprove multiple users.
    """
    user_ids = request.data.get('user_ids', [])
    
    if not user_ids:
        return Response(
            {'error': 'No user IDs provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    users = User.objects.filter(
        id__in=user_ids,
        is_approved=True
    ).exclude(user_type='ADMIN')
    
    updated_count = 0
    for user in users:
        user.is_approved = False
        user._approval_status_changed = True
        user.save()
        updated_count += 1
    
    return Response({
        'message': f'{updated_count} users disapproved successfully',
        'disapproved_count': updated_count
    })