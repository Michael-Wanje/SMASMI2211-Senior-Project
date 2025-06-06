from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User management
    path('', views.UserListCreateView.as_view(), name='user-list-create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('<int:pk>/approve/', views.UserApprovalView.as_view(), name='user-approval'),
    
    # Residents list for visitor registration
    path('residents/', views.ResidentListView.as_view(), name='resident-list'),
    
    # Statistics and bulk operations
    path('stats/', views.user_stats, name='user-stats'),
    path('bulk-approve/', views.bulk_approve_users, name='bulk-approve'),
    path('bulk-disapprove/', views.bulk_disapprove_users, name='bulk-disapprove'),
]