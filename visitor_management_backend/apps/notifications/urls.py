from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification CRUD
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('create/', views.create_notification, name='create-notification'),
    
    # Notification actions
    path('<int:pk>/mark-read/', views.mark_notification_as_read, name='mark-notification-read'),
    path('mark-all-read/', views.mark_all_notifications_as_read, name='mark-all-notifications-read'),
    path('delete-read/', views.delete_all_read_notifications, name='delete-read-notifications'),
    
    # Notification info
    path('counts/', views.notification_counts, name='notification-counts'),
    path('recent/', views.recent_notifications, name='recent-notifications'),
    
    # Bulk operations
    path('bulk-send/', views.send_bulk_notification, name='bulk-notification'),
]