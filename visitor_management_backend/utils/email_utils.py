import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from apps.notifications.models import EmailLog
import logging

logger = logging.getLogger(__name__)

def send_email_notification(recipient_email, subject, message, template_name=None, context=None):
    """
    Send email notification with proper logging
    """
    try:
        if template_name and context:
            # Use HTML template
            html_content = render_to_string(template_name, context)
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            msg.attach_alternative(html_content, "text/html")
            result = msg.send()
        else:
            # Send plain text email
            result = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        
        # Log successful email
        EmailLog.objects.create(
            recipient_email=recipient_email,
            subject=subject,
            message=message,
            status='sent'
        )
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        # Log failed email
        EmailLog.objects.create(
            recipient_email=recipient_email,
            subject=subject,
            message=message,
            status='failed',
            error_message=str(e)
        )
        
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False

def send_visit_request_email(resident, visitor, visit_request):
    """Send email notification for new visit request"""
    subject = f"New Visit Request from {visitor.full_name}"
    message = f"""
    Dear {resident.first_name},
    
    You have received a new visit request:
    
    Visitor: {visitor.full_name}
    Phone: {visitor.phone_number}
    Purpose: {visit_request.purpose}
    Requested Date: {visit_request.visit_date}
    Requested Time: {visit_request.visit_time}
    
    Please log in to your resident portal to approve or deny this request.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'resident_name': resident.first_name,
        'visitor_name': visitor.full_name,
        'visitor_phone': visitor.phone_number,
        'purpose': visit_request.purpose,
        'visit_date': visit_request.visit_date,
        'visit_time': visit_request.visit_time,
        'request_id': visit_request.id
    }
    
    return send_email_notification(
        recipient_email=resident.email,
        subject=subject,
        message=message,
        template_name='emails/visit_request.html',
        context=context
    )

def send_visit_approved_email(visitor, visit_request):
    """Send email notification when visit is approved"""
    subject = "Visit Request Approved"
    message = f"""
    Dear {visitor.full_name},
    
    Your visit request has been approved!
    
    Details:
    Resident: {visit_request.resident.first_name} {visit_request.resident.last_name}
    Date: {visit_request.visit_date}
    Time: {visit_request.visit_time}
    Purpose: {visit_request.purpose}
    
    Please arrive on time and present your ID at the security gate.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'visitor_name': visitor.full_name,
        'resident_name': f"{visit_request.resident.first_name} {visit_request.resident.last_name}",
        'visit_date': visit_request.visit_date,
        'visit_time': visit_request.visit_time,
        'purpose': visit_request.purpose
    }
    
    return send_email_notification(
        recipient_email=visitor.email,
        subject=subject,
        message=message,
        template_name='emails/visit_approved.html',
        context=context
    )

def send_visit_denied_email(visitor, visit_request, reason=None):
    """Send email notification when visit is denied"""
    subject = "Visit Request Denied"
    message = f"""
    Dear {visitor.full_name},
    
    Unfortunately, your visit request has been denied.
    
    Details:
    Resident: {visit_request.resident.first_name} {visit_request.resident.last_name}
    Date: {visit_request.visit_date}
    Time: {visit_request.visit_time}
    Purpose: {visit_request.purpose}
    """
    
    if reason:
        message += f"\nReason: {reason}"
    
    message += """
    
    You have been temporarily restricted from making new requests to this resident.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'visitor_name': visitor.full_name,
        'resident_name': f"{visit_request.resident.first_name} {visit_request.resident.last_name}",
        'visit_date': visit_request.visit_date,
        'visit_time': visit_request.visit_time,
        'purpose': visit_request.purpose,
        'denial_reason': reason
    }
    
    return send_email_notification(
        recipient_email=visitor.email,
        subject=subject,
        message=message,
        template_name='emails/visit_denied.html',
        context=context
    )

def send_security_notification_email(security_user, visitor, visit_request):
    """Send email notification to security for approved visit"""
    subject = f"Approved Visitor Alert - {visitor.full_name}"
    message = f"""
    Dear Security Team,
    
    An approved visitor is expected:
    
    Visitor: {visitor.full_name}
    Phone: {visitor.phone_number}
    National ID: {visitor.national_id}
    Visiting: {visit_request.resident.first_name} {visit_request.resident.last_name}
    Apartment: {getattr(visit_request.resident, 'apartment_number', 'N/A')}
    Purpose: {visit_request.purpose}
    Date: {visit_request.visit_date}
    Time: {visit_request.visit_time}
    
    Please allow entry when they arrive.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'visitor_name': visitor.full_name,
        'visitor_phone': visitor.phone_number,
        'visitor_id': visitor.national_id,
        'resident_name': f"{visit_request.resident.first_name} {visit_request.resident.last_name}",
        'apartment_number': getattr(visit_request.resident, 'apartment_number', 'N/A'),
        'purpose': visit_request.purpose,
        'visit_date': visit_request.visit_date,
        'visit_time': visit_request.visit_time
    }
    
    return send_email_notification(
        recipient_email=security_user.email,
        subject=subject,
        message=message,
        template_name='emails/security_notification.html',
        context=context
    )

def send_resident_registration_email(resident):
    """Send email notification for new resident registration"""
    subject = "Welcome to Visitor Management System"
    message = f"""
    Dear {resident.first_name},
    
    Welcome to our Visitor Management System!
    
    Your account has been created and is pending approval by the system administrator.
    You will receive another notification once your account is approved.
    
    Account Details:
    Name: {resident.first_name} {resident.last_name}
    Email: {resident.email}
    Apartment: {getattr(resident, 'apartment_number', 'N/A')}
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'resident_name': resident.first_name,
        'full_name': f"{resident.first_name} {resident.last_name}",
        'email': resident.email,
        'apartment_number': getattr(resident, 'apartment_number', 'N/A')
    }
    
    return send_email_notification(
        recipient_email=resident.email,
        subject=subject,
        message=message,
        template_name='emails/resident_registration.html',
        context=context
    )

def send_resident_approval_email(resident):
    """Send email notification when resident is approved"""
    subject = "Account Approved - Visitor Management System"
    message = f"""
    Dear {resident.first_name},
    
    Great news! Your account has been approved by the system administrator.
    
    You can now log in to your resident portal and start managing your visitors.
    
    Login URL: {settings.FRONTEND_URL}/login
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'resident_name': resident.first_name,
        'login_url': f"{settings.FRONTEND_URL}/login"
    }
    
    return send_email_notification(
        recipient_email=resident.email,
        subject=subject,
        message=message,
        template_name='emails/resident_approved.html',
        context=context
    )

def send_admin_new_resident_email(admin_email, resident):
    """Send email notification to admin for new resident registration"""
    subject = f"New Resident Registration - {resident.first_name} {resident.last_name}"
    message = f"""
    Dear Administrator,
    
    A new resident has registered and is awaiting approval:
    
    Name: {resident.first_name} {resident.last_name}
    Email: {resident.email}
    Phone: {resident.phone_number}
    Apartment: {getattr(resident, 'apartment_number', 'N/A')}
    Registration Date: {resident.date_joined}
    
    Please log in to the admin panel to approve or reject this registration.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'resident_name': f"{resident.first_name} {resident.last_name}",
        'resident_email': resident.email,
        'resident_phone': resident.phone_number,
        'apartment_number': getattr(resident, 'apartment_number', 'N/A'),
        'registration_date': resident.date_joined
    }
    
    return send_email_notification(
        recipient_email=admin_email,
        subject=subject,
        message=message,
        template_name='emails/admin_new_resident.html',
        context=context
    )

def send_blacklist_notification_email(visitor, resident, reason=None):
    """Send email notification when visitor is blacklisted"""
    subject = "Visitor Access Restricted"
    message = f"""
    Dear {visitor.full_name},
    
    Your access has been restricted for security reasons.
    
    You are no longer able to make visit requests to {resident.first_name} {resident.last_name}.
    """
    
    if reason:
        message += f"\nReason: {reason}"
    
    message += """
    
    If you believe this is an error, please contact the system administrator.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'visitor_name': visitor.full_name,
        'resident_name': f"{resident.first_name} {resident.last_name}",
        'blacklist_reason': reason
    }
    
    return send_email_notification(
        recipient_email=visitor.email,
        subject=subject,
        message=message,
        template_name='emails/visitor_blacklisted.html',
        context=context
    )

def send_password_reset_email(user, reset_token):
    """Send password reset email"""
    subject = "Password Reset Request"
    message = f"""
    Dear {user.first_name},
    
    You have requested to reset your password for the Visitor Management System.
    
    Please click the link below to reset your password:
    {settings.FRONTEND_URL}/reset-password?token={reset_token}
    
    This link will expire in 24 hours.
    
    If you did not request this password reset, please ignore this email.
    
    Best regards,
    Visitor Management System
    """
    
    context = {
        'user_name': user.first_name,
        'reset_url': f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    }
    
    return send_email_notification(
        recipient_email=user.email,
        subject=subject,
        message=message,
        template_name='emails/password_reset.html',
        context=context
    )

def send_bulk_notification_email(recipients, subject, message):
    """Send bulk email notifications"""
    results = []
    for recipient in recipients:
        result = send_email_notification(
            recipient_email=recipient,
            subject=subject,
            message=message
        )
        results.append({
            'recipient': recipient,
            'success': result
        })
    
    return results