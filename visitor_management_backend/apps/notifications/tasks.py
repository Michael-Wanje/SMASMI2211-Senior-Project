from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification

@shared_task
def send_email_notification(notification_id):
    """
    Send email notification to user
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
        # Only send email if user has email and wants notifications
        if not user.email or not getattr(user, 'email_notifications', True):
            return False
        
        subject = f"[Visitor Management] {notification.title}"
        
        # Create HTML and text versions of the email
        html_message = render_to_string('emails/notification.html', {
            'user': user,
            'notification': notification,
            'site_name': 'Visitor Management System'
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Notification.DoesNotExist:
        return False
    except Exception as e:
        # Log the error in production
        print(f"Error sending notification email: {str(e)}")
        return False

@shared_task
def send_visit_request_email(visit_request_id):
    """
    Send email notification for visit requests
    """
    try:
        from apps.visitors.models import VisitRequest
        
        visit_request = VisitRequest.objects.get(id=visit_request_id)
        resident = visit_request.resident
        
        if not resident.email:
            return False
        
        subject = f"New Visit Request from {visit_request.visitor.name}"
        
        html_message = render_to_string('emails/visit_request.html', {
            'resident': resident,
            'visit_request': visit_request,
            'visitor': visit_request.visitor,
            'site_name': 'Visitor Management System'
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[resident.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending visit request email: {str(e)}")
        return False

@shared_task
def send_visit_approval_email(visit_request_id):
    """
    Send email notification when visit is approved
    """
    try:
        from apps.visitors.models import VisitRequest
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        visit_request = VisitRequest.objects.get(id=visit_request_id)
        
        # Send to security personnel
        security_users = User.objects.filter(user_type='security', is_active=True)
        
        for security_user in security_users:
            if not security_user.email:
                continue
                
            subject = f"Visit Request Approved - {visit_request.visitor.name}"
            
            html_message = render_to_string('emails/visit_approved.html', {
                'security_user': security_user,
                'visit_request': visit_request,
                'visitor': visit_request.visitor,
                'resident': visit_request.resident,
                'site_name': 'Visitor Management System'
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[security_user.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        return True
        
    except Exception as e:
        print(f"Error sending visit approval email: {str(e)}")
        return False

@shared_task
def cleanup_old_notifications():
    """
    Clean up old read notifications (older than 30 days)
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date
        ).delete()[0]
        
        return f"Cleaned up {deleted_count} old notifications"
        
    except Exception as e:
        print(f"Error cleaning up notifications: {str(e)}")
        return False