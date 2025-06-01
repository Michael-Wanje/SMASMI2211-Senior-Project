import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from jinja2 import Template
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
    
    def _create_smtp_connection(self):
        """Create and return SMTP connection"""
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls(context=context)
            server.login(self.username, self.password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {str(e)}")
            raise
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Send email with HTML content
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    with open(attachment["file_path"], "rb") as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment["filename"]}'
                        )
                        message.attach(part)
            
            # Send email
            with self._create_smtp_connection() as server:
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_visit_request_notification(self, resident_email: str, visitor_name: str, purpose: str, visit_date: str) -> bool:
        """Send visit request notification to resident"""
        subject = "New Visitor Request"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                .header { background-color: #007bff; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }
                .button { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Visitor Management System</h2>
                    <h3>New Visitor Request</h3>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You have received a new visitor request with the following details:</p>
                    <ul>
                        <li><strong>Visitor Name:</strong> {{ visitor_name }}</li>
                        <li><strong>Purpose of Visit:</strong> {{ purpose }}</li>
                        <li><strong>Requested Date:</strong> {{ visit_date }}</li>
                    </ul>
                    <p>Please log in to your resident portal to approve or deny this request.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Visitor Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            visitor_name=visitor_name,
            purpose=purpose,
            visit_date=visit_date
        )
        
        return self.send_email(resident_email, subject, html_content)
    
    def send_visit_approval_notification(self, visitor_email: str, visitor_name: str, resident_name: str) -> bool:
        """Send visit approval notification to visitor"""
        subject = "Visit Request Approved"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                .header { background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Visit Request Approved</h2>
                </div>
                <div class="content">
                    <p>Dear {{ visitor_name }},</p>
                    <p>Great news! Your visit request has been approved by {{ resident_name }}.</p>
                    <p>Please proceed to the security gate at your scheduled time. Make sure to bring a valid ID for verification.</p>
                    <p>Thank you for using our visitor management system.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Visitor Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(visitor_name=visitor_name, resident_name=resident_name)
        
        return self.send_email(visitor_email, subject, html_content)
    
    def send_visit_denial_notification(self, visitor_email: str, visitor_name: str, reason: str) -> bool:
        """Send visit denial notification to visitor"""
        subject = "Visit Request Denied"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Visit Request Denied</h2>
                </div>
                <div class="content">
                    <p>Dear {{ visitor_name }},</p>
                    <p>We regret to inform you that your visit request has been denied.</p>
                    {% if reason %}
                    <p><strong>Reason:</strong> {{ reason }}</p>
                    {% endif %}
                    <p>If you have any questions, please contact the resident directly.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Visitor Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(visitor_name=visitor_name, reason=reason)
        
        return self.send_email(visitor_email, subject, html_content)
    
    def send_security_notification(self, security_email: str, visitor_name: str, resident_name: str, action: str) -> bool:
        """Send notification to security personnel"""
        subject = f"Visitor Update - {action}"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                .header { background-color: #17a2b8; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Security Notification</h2>
                </div>
                <div class="content">
                    <p>Security Team,</p>
                    <p>Please be informed that a visitor request has been {{ action }}:</p>
                    <ul>
                        <li><strong>Visitor:</strong> {{ visitor_name }}</li>
                        <li><strong>Resident:</strong> {{ resident_name }}</li>
                        <li><strong>Status:</strong> {{ action }}</li>
                    </ul>
                    <p>Please update your security logs accordingly.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Visitor Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            visitor_name=visitor_name,
            resident_name=resident_name,
            action=action
        )
        
        return self.send_email(security_email, subject, html_content)
    
    def send_password_reset_email(self, user_email: str, user_name: str, reset_token: str) -> bool:
        """Send password reset email"""
        subject = "Password Reset Request"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                .header { background-color: #ffc107; color: black; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }
                .token { background-color: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Password Reset Request</h2>
                </div>
                <div class="content">
                    <p>Dear {{ user_name }},</p>
                    <p>You have requested a password reset for your account. Please use the following reset token:</p>
                    <div class="token">{{ reset_token }}</div>
                    <p><strong>Important:</strong> This token will expire in 24 hours for security reasons.</p>
                    <p>If you did not request this password reset, please ignore this email and contact support immediately.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Visitor Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(user_name=user_name, reset_token=reset_token)
        
        return self.send_email(user_email, subject, html_content)

# Create singleton instance
email_service = EmailService()