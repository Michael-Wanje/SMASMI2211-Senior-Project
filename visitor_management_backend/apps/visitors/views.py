from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Visitor, VisitRequest, BlacklistedVisitor
from .serializers import (
    VisitorSerializer, VisitRequestSerializer, VisitRequestCreateSerializer,
    VisitRequestUpdateSerializer, BlacklistedVisitorSerializer
)
from .permissions import IsResidentOrSecurity, IsSecurityOrAdmin, IsResidentOrAdmin
from apps.notifications.models import Notification

User = get_user_model()

class VisitorListCreateView(generics.ListCreateAPIView):
    """
    List all visitors or create a new visitor
    """
    queryset = Visitor.objects.all()
    serializer_class = VisitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Visitor.objects.all()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search) |
                Q(id_number__icontains=search)
            )
        
        return queryset.order_by('-created_at')

class VisitorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a visitor
    """
    queryset = Visitor.objects.all()
    serializer_class = VisitorSerializer
    permission_classes = [IsAuthenticated, IsSecurityOrAdmin]

class VisitRequestListCreateView(generics.ListCreateAPIView):
    """
    List all visit requests or create a new visit request
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VisitRequestCreateSerializer
        return VisitRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = VisitRequest.objects.all()

        # Filter based on user type
        if user.user_type == 'resident':
            queryset = queryset.filter(resident=user)
        elif user.user_type == 'security':
            # Security can see all requests
            pass
        elif user.user_type == 'admin':
            # Admin can see all requests
            pass

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(visit_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(visit_date__lte=date_to)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        
        # If resident is creating, auto-approve
        if user.user_type == 'resident':
            visit_request = serializer.save(resident=user, status='approved', approval_date=timezone.now())
            
            # Notify security personnel
            security_users = User.objects.filter(user_type='security', is_active=True)
            for security_user in security_users:
                Notification.objects.create(
                    user=security_user,
                    title='New Visit Request Approved',
                    message=f'Resident {user.get_full_name()} has registered a visitor: {visit_request.visitor.name}',
                    notification_type='visit_approved'
                )
        else:
            visit_request = serializer.save()
            
            # Notify resident
            Notification.objects.create(
                user=visit_request.resident,
                title='New Visit Request',
                message=f'You have a new visit request from {visit_request.visitor.name}',
                notification_type='visit_request'
            )

class VisitRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a visit request
    """
    queryset = VisitRequest.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return VisitRequestUpdateSerializer
        return VisitRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = VisitRequest.objects.all()

        if user.user_type == 'resident':
            queryset = queryset.filter(resident=user)
        
        return queryset

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsResidentOrAdmin])
def approve_visit_request(request, pk):
    """
    Approve a visit request
    """
    visit_request = get_object_or_404(VisitRequest, pk=pk)
    
    # Check if user is the resident or admin
    if request.user.user_type == 'resident' and visit_request.resident != request.user:
        return Response({'error': 'You can only approve your own visit requests'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    if visit_request.status != 'pending':
        return Response({'error': 'Visit request is not pending'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request.status = 'approved'
    visit_request.approval_date = timezone.now()
    visit_request.save()
    
    # Notify security personnel
    security_users = User.objects.filter(user_type='security', is_active=True)
    for security_user in security_users:
        Notification.objects.create(
            user=security_user,
            title='Visit Request Approved',
            message=f'Visit request for {visit_request.visitor.name} to {visit_request.resident.get_full_name()} has been approved.',
            notification_type='visit_approved'
        )
    
    serializer = VisitRequestSerializer(visit_request)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsResidentOrAdmin])
def deny_visit_request(request, pk):
    """
    Deny a visit request and blacklist the visitor
    """
    visit_request = get_object_or_404(VisitRequest, pk=pk)
    
    # Check if user is the resident or admin
    if request.user.user_type == 'resident' and visit_request.resident != request.user:
        return Response({'error': 'You can only deny your own visit requests'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    if visit_request.status != 'pending':
        return Response({'error': 'Visit request is not pending'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request.status = 'denied'
    visit_request.save()
    
    # Blacklist visitor for this resident
    reason = request.data.get('reason', 'Visit request denied')
    BlacklistedVisitor.objects.get_or_create(
        visitor=visit_request.visitor,
        resident=visit_request.resident,
        defaults={'reason': reason}
    )
    
    serializer = VisitRequestSerializer(visit_request)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecurityOrAdmin])
def record_entry(request):
    """
    Security personnel records visitor entry
    """
    visit_request_id = request.data.get('visit_request_id')
    
    if not visit_request_id:
        return Response({'error': 'Visit request ID is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request = get_object_or_404(VisitRequest, pk=visit_request_id)
    
    if visit_request.status != 'approved':
        return Response({'error': 'Visit request must be approved first'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request.entry_time = timezone.now()
    visit_request.security_personnel = request.user
    visit_request.save()
    
    serializer = VisitRequestSerializer(visit_request)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecurityOrAdmin])
def record_exit(request):
    """
    Security personnel records visitor exit
    """
    visit_request_id = request.data.get('visit_request_id')
    
    if not visit_request_id:
        return Response({'error': 'Visit request ID is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request = get_object_or_404(VisitRequest, pk=visit_request_id)
    
    if not visit_request.entry_time:
        return Response({'error': 'Visitor must have entered first'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    if visit_request.exit_time:
        return Response({'error': 'Exit time already recorded'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    visit_request.exit_time = timezone.now()
    visit_request.save()
    
    serializer = VisitRequestSerializer(visit_request)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecurityOrAdmin])
def walk_in_visitor(request):
    """
    Record a walk-in visitor and notify resident
    """
    serializer = VisitRequestCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        visit_request = serializer.save()
        
        # Notify resident
        Notification.objects.create(
            user=visit_request.resident,
            title='Walk-in Visitor',
            message=f'Walk-in visitor {visit_request.visitor.name} is requesting to see you',
            notification_type='walk_in_visitor'
        )
        
        response_serializer = VisitRequestSerializer(visit_request)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BlacklistedVisitorListView(generics.ListAPIView):
    """
    List all blacklisted visitors
    """
    serializer_class = BlacklistedVisitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = BlacklistedVisitor.objects.all()

        if user.user_type == 'resident':
            queryset = queryset.filter(resident=user)
        
        return queryset.order_by('-blacklisted_at')

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsResidentOrAdmin])
def remove_from_blacklist(request, pk):
    """
    Remove visitor from blacklist
    """
    blacklisted_visitor = get_object_or_404(BlacklistedVisitor, pk=pk)
    
    # Check if user is the resident or admin
    if request.user.user_type == 'resident' and blacklisted_visitor.resident != request.user:
        return Response({'error': 'You can only remove visitors from your own blacklist'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    blacklisted_visitor.delete()
    return Response({'message': 'Visitor removed from blacklist'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visitor_statistics(request):
    """
    Get visitor statistics
    """
    user = self.request.user
    
    # Base queryset
    if user.user_type == 'resident':
        visit_requests = VisitRequest.objects.filter(resident=user)
    else:
        visit_requests = VisitRequest.objects.all()
    
    # Calculate statistics
    total_requests = visit_requests.count()
    approved_requests = visit_requests.filter(status='approved').count()
    denied_requests = visit_requests.filter(status='denied').count()
    pending_requests = visit_requests.filter(status='pending').count()
    
    # Today's statistics
    today = timezone.now().date()
    today_requests = visit_requests.filter(visit_date=today).count()
    today_entries = visit_requests.filter(entry_time__date=today).count()
    
    return Response({
        'total_requests': total_requests,
        'approved_requests': approved_requests,
        'denied_requests': denied_requests,
        'pending_requests': pending_requests,
        'today_requests': today_requests,
        'today_entries': today_entries,
    })