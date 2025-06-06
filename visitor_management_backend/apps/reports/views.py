from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.visitors.models import Visitor, VisitRequest, VisitorEntry
from apps.users.models import User
from apps.notifications.models import Notification
from .serializers import (
    DailyVisitorReportSerializer,
    MonthlyReportSerializer,
    ResidentReportSerializer,
    SystemStatsSerializer
)
from .utils import generate_pdf_report, generate_excel_report
from utils.permissions import IsAdminUser, IsSecurityOrAdmin

class DailyVisitorReportView(generics.ListAPIView):
    serializer_class = DailyVisitorReportSerializer
    permission_classes = [IsAuthenticated, IsSecurityOrAdmin]
    
    def get_queryset(self):
        date = self.request.query_params.get('date')
        if date:
            try:
                report_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                report_date = timezone.now().date()
        else:
            report_date = timezone.now().date()
        
        return VisitorEntry.objects.filter(
            entry_time__date=report_date
        ).select_related('visitor', 'visit_request', 'recorded_by')

class MonthlyReportView(generics.ListAPIView):
    serializer_class = MonthlyReportSerializer
    permission_classes = [IsAuthenticated, IsSecurityOrAdmin]
    
    def get_queryset(self):
        year = int(self.request.query_params.get('year', timezone.now().year))
        month = int(self.request.query_params.get('month', timezone.now().month))
        
        return VisitorEntry.objects.filter(
            entry_time__year=year,
            entry_time__month=month
        ).select_related('visitor', 'visit_request')

class ResidentReportView(generics.ListAPIView):
    serializer_class = ResidentReportSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return User.objects.filter(
            user_type='resident',
            is_approved=True
        ).annotate(
            total_requests=Count('visit_requests'),
            approved_requests=Count('visit_requests', filter=Q(visit_requests__status='approved')),
            denied_requests=Count('visit_requests', filter=Q(visit_requests__status='denied')),
            pending_requests=Count('visit_requests', filter=Q(visit_requests__status='pending'))
        )

class SystemStatsView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        stats = {
            'total_residents': User.objects.filter(user_type='resident', is_approved=True).count(),
            'pending_residents': User.objects.filter(user_type='resident', is_approved=False).count(),
            'total_visitors': Visitor.objects.count(),
            'blacklisted_visitors': Visitor.objects.filter(is_blacklisted=True).count(),
            'today_entries': VisitorEntry.objects.filter(entry_time__date=today).count(),
            'pending_requests': VisitRequest.objects.filter(status='pending').count(),
            'last_30_days_entries': VisitorEntry.objects.filter(
                entry_time__date__gte=last_30_days
            ).count(),
            'unread_notifications': Notification.objects.filter(is_read=False).count(),
        }
        
        serializer = SystemStatsSerializer(stats)
        return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecurityOrAdmin])
def download_daily_report(request):
    date = request.query_params.get('date')
    format_type = request.query_params.get('format', 'pdf')  # pdf or excel
    
    if date:
        try:
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    entries = VisitorEntry.objects.filter(
        entry_time__date=report_date
    ).select_related('visitor', 'visit_request', 'recorded_by')
    
    if format_type == 'excel':
        response = generate_excel_report(entries, report_date)
    else:
        response = generate_pdf_report(entries, report_date)
    
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def visitor_trends(request):
    """Get visitor trends for the last 30 days"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)
    
    trends = []
    current_date = start_date
    
    while current_date <= end_date:
        daily_count = VisitorEntry.objects.filter(
            entry_time__date=current_date
        ).count()
        
        trends.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': daily_count
        })
        current_date += timedelta(days=1)
    
    return Response({
        'trends': trends,
        'period': f"{start_date} to {end_date}"
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def resident_activity_report(request):
    """Get resident activity report"""
    resident_id = request.query_params.get('resident_id')
    days = int(request.query_params.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    if resident_id:
        residents = User.objects.filter(id=resident_id, user_type='resident')
    else:
        residents = User.objects.filter(user_type='resident', is_approved=True)
    
    report_data = []
    
    for resident in residents:
        requests = VisitRequest.objects.filter(
            resident=resident,
            created_at__date__gte=start_date
        )
        
        activity = {
            'resident_id': resident.id,
            'resident_name': f"{resident.first_name} {resident.last_name}",
            'email': resident.email,
            'apartment_number': getattr(resident, 'apartment_number', 'N/A'),
            'total_requests': requests.count(),
            'approved_requests': requests.filter(status='approved').count(),
            'denied_requests': requests.filter(status='denied').count(),
            'pending_requests': requests.filter(status='pending').count(),
            'entries_count': VisitorEntry.objects.filter(
                visit_request__resident=resident,
                entry_time__date__gte=start_date
            ).count()
        }
        report_data.append(activity)
    
    return Response({
        'report_data': report_data,
        'period': f"{start_date} to {end_date}",
        'total_residents': len(report_data)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecurityOrAdmin])
def blacklisted_visitors_report(request):
    """Get report of blacklisted visitors"""
    blacklisted_visitors = Visitor.objects.filter(
        is_blacklisted=True
    ).select_related('blacklisted_by')
    
    report_data = []
    for visitor in blacklisted_visitors:
        data = {
            'visitor_id': visitor.id,
            'full_name': visitor.full_name,
            'phone_number': visitor.phone_number,
            'email': visitor.email,
            'national_id': visitor.national_id,
            'blacklisted_date': visitor.blacklisted_date,
            'blacklisted_by': f"{visitor.blacklisted_by.first_name} {visitor.blacklisted_by.last_name}" if visitor.blacklisted_by else None,
            'blacklist_reason': visitor.blacklist_reason,
        }
        report_data.append(data)
    
    return Response({
        'blacklisted_visitors': report_data,
        'total_count': len(report_data)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def security_alerts_report(request):
    """Get security alerts and incidents report"""
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    # Get security-related notifications
    security_notifications = Notification.objects.filter(
        notification_type__in=['security_alert', 'visitor_blacklisted'],
        created_at__date__gte=start_date
    ).select_related('sender', 'recipient')
    
    alerts_data = []
    for notification in security_notifications:
        alert = {
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'sender': f"{notification.sender.first_name} {notification.sender.last_name}" if notification.sender else 'System',
            'recipient': f"{notification.recipient.first_name} {notification.recipient.last_name}",
            'created_at': notification.created_at,
            'is_read': notification.is_read
        }
        alerts_data.append(alert)
    
    return Response({
        'security_alerts': alerts_data,
        'period': f"{start_date} to {end_date}",
        'total_alerts': len(alerts_data),
        'unread_alerts': len([alert for alert in alerts_data if not alert['is_read']])
    })