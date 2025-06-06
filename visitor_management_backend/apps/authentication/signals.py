from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_notification(sender, instance, created, **kwargs):
    """
    Create notification when a new user registers (except admin).
    """
    if created and instance.user_type != 'ADMIN':
        # Get all admin users
        admin_users = User.objects.filter(user_type='ADMIN', is_active=True)
        
        # Create notification for each admin
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title='New User Registration',
                message=f'New {instance.get_user_type_display().lower()} {instance.get_full_name()} has registered and needs approval.',
                notification_type='USER_REGISTRATION',
                related_user=instance
            )

@receiver(post_save, sender=User)
def user_approval_notification(sender, instance, created, **kwargs):
    """
    Create notification when user is approved or rejected.
    """
    if not created and hasattr(instance, '_approval_status_changed'):
        if instance.is_approved:
            Notification.objects.create(
                user=instance,
                title='Account Approved',
                message='Your account has been approved. You can now access the system.',
                notification_type='APPROVAL'
            )
        else:
            Notification.objects.create(
                user=instance,
                title='Account Status Updated',
                message='Your account status has been updated. Please contact administrator for more information.',
                notification_type='APPROVAL'
            )
        
        # Clean up the flag
        delattr(instance, '_approval_status_changed')