import re
from typing import Optional, List
from datetime import datetime
import phonenumbers
from phonenumbers import NumberParseException
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class Validators:
    """Collection of validation functions"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))

    @staticmethod
    def validate_phone_number(phone: str, country_code: str = "KE") -> bool:
        """Validate phone number format for Kenya"""
        if not phone:
            return False
        
        try:
            # Remove any spaces or special characters except +
            cleaned_phone = re.sub(r'[^\d+]', '', phone.strip())
            
            # Parse the phone number
            parsed_number = phonenumbers.parse(cleaned_phone, country_code)
            
            # Check if the number is valid
            return phonenumbers.is_valid_number(parsed_number)
        except NumberParseException:
            # Fallback to basic validation for Kenyan numbers
            return Validators._validate_kenyan_phone_basic(phone)

    @staticmethod
    def _validate_kenyan_phone_basic(phone: str) -> bool:
        """Basic validation for Kenyan phone numbers"""
        # Remove spaces and special characters
        cleaned = re.sub(r'[^\d+]', '', phone.strip())
        
        # Kenyan mobile patterns
        patterns = [
            r'^\+254[17]\d{8}$',  # +254 7XX XXX XXX or +254 1XX XXX XXX
            r'^254[17]\d{8}$',    # 254 7XX XXX XXX or 254 1XX XXX XXX
            r'^0[17]\d{8}$',      # 07XX XXX XXX or 01XX XXX XXX
            r'^[17]\d{8}$'        # 7XX XXX XXX or 1XX XXX XXX
        ]
        
        return any(re.match(pattern, cleaned) for pattern in patterns)

    @staticmethod
    def validate_password(password: str) -> tuple[bool, List[str]]:
        """
        Validate password strength
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        if not password:
            errors.append("Password is required")
            return False, errors
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_passwords = ['password', '12345678', 'qwerty123', 'admin123']
        if password.lower() in weak_passwords:
            errors.append("Password is too common, please choose a stronger password")
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_name(name: str, min_length: int = 2, max_length: int = 50) -> bool:
        """Validate name format"""
        if not name:
            return False
        
        name = name.strip()
        
        # Check length
        if len(name) < min_length or len(name) > max_length:
            return False
        
        # Allow letters, spaces, hyphens, and apostrophes
        pattern = r'^[a-zA-Z\s\-\']+$'
        return bool(re.match(pattern, name))

    @staticmethod
    def validate_id_number(id_number: str) -> bool:
        """Validate Kenyan ID number format"""
        if not id_number:
            return False
        
        # Remove any spaces
        cleaned_id = re.sub(r'\s+', '', id_number.strip())
        
        # Kenyan ID should be 6-8 digits
        pattern = r'^\d{6,8}$'
        return bool(re.match(pattern, cleaned_id))

    @staticmethod
    def validate_visit_purpose(purpose: str) -> bool:
        """Validate visit purpose"""
        if not purpose:
            return False
        
        purpose = purpose.strip()
        
        # Check length (should be reasonable)
        if len(purpose) < 3 or len(purpose) > 200:
            return False
        
        # Basic check for meaningful content
        if purpose.lower() in ['test', 'xxx', '123', 'none']:
            return False
        
        return True

    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
        """Validate date range"""
        if not start_date or not end_date:
            return False
        
        # Start date should be before end date
        if start_date >= end_date:
            return False
        
        # Dates should not be too far in the future
        max_future_date = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
        if start_date > max_future_date or end_date > max_future_date:
            return False
        
        return True

    @staticmethod
    def validate_user_role(role: str) -> bool:
        """Validate user role"""
        valid_roles = ['admin', 'resident', 'security', 'visitor']
        return role and role.lower() in valid_roles

    @staticmethod
    def validate_visit_status(status: str) -> bool:
        """Validate visit request status"""
        valid_statuses = ['pending', 'approved', 'denied', 'cancelled', 'completed']
        return status and status.lower() in valid_statuses

    @staticmethod
    def sanitize_input(input_str: str, max_length: int = None) -> str:
        """Sanitize user input"""
        if not input_str:
            return ""
        
        # Remove leading/trailing whitespace
        sanitized = input_str.strip()
        
        # Remove any potential script tags or HTML
        sanitized = re.sub(r'<[^>]*>', '', sanitized)
        
        # Remove any potential SQL injection characters
        sanitized = re.sub(r'[;\'"\\]', '', sanitized)
        
        # Limit length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized

    @staticmethod
    def validate_notification_type(notification_type: str) -> bool:
        """Validate notification type"""
        valid_types = [
            'visit_request', 'visit_approval', 'visit_denial', 
            'visit_status', 'security_alert', 'system', 
            'blacklist_alert', 'reminder'
        ]
        return notification_type and notification_type.lower() in valid_types

    @staticmethod
    def validate_search_query(query: str) -> bool:
        """Validate search query"""
        if not query:
            return False
        
        query = query.strip()
        
        # Check minimum length
        if len(query) < 2:
            return False
        
        # Check maximum length
        if len(query) > 100:
            return False
        
        # Ensure it's not just special characters
        if re.match(r'^[^a-zA-Z0-9\s]+$', query):
            return False
        
        return True

    @staticmethod
    def validate_pagination_params(page: int, limit: int) -> tuple[bool, str]:
        """Validate pagination parameters"""
        if page < 1:
            return False, "Page number must be greater than 0"
        
        if limit < 1:
            return False, "Limit must be greater than 0"
        
        if limit > 100:
            return False, "Limit cannot exceed 100"
        
        return True, ""

    @staticmethod
    def validate_apartment_number(apartment_number: str) -> bool:
        """Validate apartment number format"""
        if not apartment_number:
            return False
        
        apartment_number = apartment_number.strip()
        
        # Allow alphanumeric with some special characters
        pattern = r'^[A-Za-z0-9\-\/\s]{1,20}$'
        return bool(re.match(pattern, apartment_number))

    @staticmethod
    def validate_address(address: str) -> bool:
        """Validate address format"""
        if not address:
            return False
        
        address = address.strip()
        
        # Check length
        if len(address) < 5 or len(address) > 200:
            return False
        
        # Should contain some letters and numbers
        has_letters = bool(re.search(r'[a-zA-Z]', address))
        has_numbers = bool(re.search(r'\d', address))
        
        return has_letters and has_numbers

class BusinessLogicValidator:
    """Business logic validation functions"""
    
    @staticmethod
    def can_visitor_request_visit(visitor_id: int, resident_id: int, db) -> tuple[bool, str]:
        """Check if visitor can request a visit to a specific resident"""
        from app.models.blacklist import Blacklist
        
        try:
            # Check if visitor is blacklisted by this resident
            blacklist_entry = db.query(Blacklist).filter(
                Blacklist.visitor_id == visitor_id,
                Blacklist.resident_id == resident_id,
                Blacklist.is_active == True
            ).first()
            
            if blacklist_entry:
                return False, "You are blacklisted by this resident and cannot request a visit"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error checking visitor blacklist status: {str(e)}")
            return False, "Unable to verify visitor status"

    @staticmethod
    def can_resident_approve_visit(resident_id: int, visit_request_id: int, db) -> tuple[bool, str]:
        """Check if resident can approve a specific visit request"""
        from app.models.visit_request import VisitRequest
        
        try:
            visit_request = db.query(VisitRequest).filter(
                VisitRequest.id == visit_request_id,
                VisitRequest.resident_id == resident_id
            ).first()
            
            if not visit_request:
                return False, "Visit request not found or not associated with this resident"
            
            if visit_request.status != "pending":
                return False, f"Visit request is already {visit_request.status}"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error checking visit request approval eligibility: {str(e)}")
            return False, "Unable to verify visit request status"

    @staticmethod
    def validate_visit_time(visit_date: datetime) -> tuple[bool, str]:
        """Validate visit timing"""
        from datetime import timedelta
        current_time = datetime.utcnow()
        
        # Visit should not be in the past
        if visit_date < current_time:
            return False, "Visit date cannot be in the past"
        
        # Visit should not be too far in the future (e.g., more than 30 days)
        max_future_date = current_time + timedelta(days=30)
        if visit_date > max_future_date:
            return False, "Visit date cannot be more than 30 days in the future"
        
        # Check if it's within visiting hours (assuming 6 AM to 10 PM)
        visit_hour = visit_date.hour
        if visit_hour < 6 or visit_hour > 22:
            return False, "Visits are only allowed between 6:00 AM and 10:00 PM"
        
        return True, ""

    @staticmethod
    def validate_duplicate_visit_request(visitor_id: int, resident_id: int, 
                                       visit_date: datetime, db) -> tuple[bool, str]:
        """Check for duplicate visit requests"""
        from app.models.visit_request import VisitRequest
        from datetime import timedelta
        
        try:
            # Check for existing pending or approved requests within the same day
            start_of_day = visit_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            existing_request = db.query(VisitRequest).filter(
                VisitRequest.visitor_id == visitor_id,
                VisitRequest.resident_id == resident_id,
                VisitRequest.visit_date >= start_of_day,
                VisitRequest.visit_date < end_of_day,
                VisitRequest.status.in_(["pending", "approved"])
            ).first()
            
            if existing_request:
                return False, "You already have a visit request for this resident on this date"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error checking duplicate visit requests: {str(e)}")
            return False, "Unable to verify duplicate requests"