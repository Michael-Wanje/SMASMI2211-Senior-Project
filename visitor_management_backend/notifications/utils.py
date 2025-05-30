from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import NotificationTemplate, Notification
import logging

logger = logging.getLogger(__name__)

def send_visitor_notification(visitor, notification_type, recipient, extra_context=None):
    """
    Send notification about visitor-related events
    """
    try:
        # Get notification template
        template = NotificationTemplate.objects.filter(
            template_type=notification_type,
            is_active=True
        ).first()
        
        if not template:
            logger.warning(f"No template found for notification type: {notification_type}")
            return False
        
        # Prepare context
        context = {
            'visitor': visitor,
            'recipient': recipient,
            'resident': visitor.resident,
            'visit_date': visitor.visit_date,
            'visit_time': visitor.visit_time,
            'purpose': visitor.get_purpose_display(),
            'status': visitor.get_status_display(),
        }
        
        if extra_context:
            context.update(extra_context)
        
        # Generate email content
        subject = template.subject.format(**context)
        message = template.email_body.format(**context)
        
        # Create notification record
        notification = Notification.objects.create(
            recipient=recipient,
            title=subject,
            message=message,
            notification_type=notification_type
        )
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
            notification.email_sent = True
            notification.save()
            logger.info(f"Email sent successfully to {recipient.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient.email}: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

def send_security_alert(message, recipients=None):
    """
    Send security alert to admin and security users
    """
    try:
        from authentication.models import User
        
        if not recipients:
            recipients = User.objects.filter(
                user_type__in=['admin', 'security'],
                is_active=True
            )
        
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                title="Security Alert",
                message=message,
                notification_type="security_alert"
            )
            
            # Send email
            try:
                send_mail(
                    subject="Security Alert - Visitor Management System",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send security alert email: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending security alert: {str(e)}")
        return False

def create_default_templates():
    """
    Create default notification templates
    """
    templates = [
        {
            'template_type': 'new_visitor_request',
            'subject': 'New Visitor Request - {visitor.full_name}',
            'email_body': '''
Hello {recipient.first_name},

You have received a new visitor request:

Visitor: {visitor.full_name}
Phone: {visitor.phone_number}
Purpose: {purpose}
Visit Date: {visit_date}
Visit Time: {visit_time}
Company: {visitor.company}

Please log in to the system to approve or deny this request.

Best regards,
Visitor Management System
            '''
        },
        {
            'template_type': 'visitor_approved',
            'subject': 'Visitor Request Approved - {visitor.full_name}',
            'email_body': '''
Hello,

Your visitor request has been approved:

Visitor: {visitor.full_name}
Visit Date: {visit_date}
Visit Time: {visit_time}
Status: Approved

The visitor can now proceed with their visit as scheduled.

Best regards,
Visitor Management System
            '''
        },
        {
            'template_type': 'visitor_denied',
            'subject': 'Visitor Request Denied - {visitor.full_name}',
            'email_body': '''
Hello,

Your visitor request has been denied:

Visitor: {visitor.full_name}
Visit Date: {visit_date}
Visit Time: {visit_time}
Status: Denied

Please contact the resident or security for more information.

Best regards,
Visitor Management System
            '''
        },
        {
            'template_type': 'visitor_checked_in',
            'subject': 'Visitor Checked In - {visitor.full_name}',
            'email_body': '''
Hello {recipient.first_name},

Your visitor has checked in:

Visitor: {visitor.full_name}
Check-in Time: {visitor.checked_in_at}
Purpose: {purpose}

Best regards,
Visitor Management System
            '''
        },
        {
            'template_type': 'visitor_checked_out',
            'subject': 'Visitor Checked Out - {visitor.full_name}',
            'email_body': '''
Hello {recipient.first_name},

Your visitor has checked out:

Visitor: {visitor.full_name}
Check-out Time: {visitor.checked_out_at}
Visit Duration: {visit_duration}

Best regards,
Visitor Management System
            '''
        }
    ]
    
    for template_data in templates:
        NotificationTemplate.objects.get_or_create(
            template_type=template_data['template_type'],
            defaults=template_data
        )