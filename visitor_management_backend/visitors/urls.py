from django.urls import path
from . import views

urlpatterns = [
    path('', views.VisitorListCreateView.as_view(), name='visitor-list-create'),
    path('<int:pk>/', views.VisitorDetailView.as_view(), name='visitor-detail'),
    path('<int:pk>/approve/', views.approve_visitor, name='approve-visitor'),
    path('<int:pk>/checkin/', views.check_in_visitor, name='checkin-visitor'),
    path('<int:pk>/checkout/', views.check_out_visitor, name='checkout-visitor'),
    path('stats/', views.visitor_stats, name='visitor-stats'),
    path('dashboard/', views.dashboard_data, name='dashboard-data'),
]