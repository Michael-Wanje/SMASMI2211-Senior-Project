from django.urls import path
from . import views

app_name = 'visitors'

urlpatterns = [
    # Visitor URLs
    path('visitors/', views.VisitorListCreateView.as_view(), name='visitor-list-create'),
    path('visitors/<int:pk>/', views.VisitorDetailView.as_view(), name='visitor-detail'),
    
    # Visit Request URLs
    path('visit-requests/', views.VisitRequestListCreateView.as_view(), name='visit-request-list-create'),
    path('visit-requests/<int:pk>/', views.VisitRequestDetailView.as_view(), name='visit-request-detail'),
    path('visit-requests/<int:pk>/approve/', views.approve_visit_request, name='approve-visit-request'),
    path('visit-requests/<int:pk>/deny/', views.deny_visit_request, name='deny-visit-request'),
    
    # Security URLs
    path('record-entry/', views.record_entry, name='record-entry'),
    path('record-exit/', views.record_exit, name='record-exit'),
    path('walk-in-visitor/', views.walk_in_visitor, name='walk-in-visitor'),
    
    # Blacklist URLs
    path('blacklisted-visitors/', views.BlacklistedVisitorListView.as_view(), name='blacklisted-visitors'),
    path('blacklisted-visitors/<int:pk>/remove/', views.remove_from_blacklist, name='remove-from-blacklist'),
    
    # Statistics
    path('statistics/', views.visitor_statistics, name='visitor-statistics'),
]