from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('password-reset/request/', views.request_password_reset, name='password_reset_request'),
    path('password-reset/confirm/', views.confirm_password_reset, name='password_reset_confirm'),
    path('change-password/', views.change_password, name='change_password'),
    path('api/reports/', include('apps.reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)