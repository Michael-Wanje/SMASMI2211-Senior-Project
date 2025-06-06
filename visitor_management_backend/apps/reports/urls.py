from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Daily Reports
    path('daily/', views.DailyVisitorReportView.as_view(), name='daily-report'),
    path('daily/download/', views.download_daily_report, name='download-daily-report'),
    
    # Monthly Reports
    path('monthly/', views.MonthlyReportView.as_view(), name='monthly-report'),
    
    # Resident Reports
    path('residents/', views.ResidentReportView.as_view(), name='resident-report'),
    path('residents/activity/', views.resident_activity_report, name='resident-activity-report'),
    
    # System Statistics
    path('stats/', views.SystemStatsView.as_view(), name='system-stats'),
    path('trends/', views.visitor_trends, name='visitor-trends'),
    
    # Security Reports
    path('blacklisted/', views.blacklisted_visitors_report, name='blacklisted-visitors-report'),
    path('security-alerts/', views.security_alerts_report, name='security-alerts-report'),
]