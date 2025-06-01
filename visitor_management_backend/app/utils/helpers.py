from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import secrets
import string
from sqlalchemy.orm import Session
import logging
import json
from functools import wraps
import time

logger = logging.getLogger(__name__)

class DateTimeHelper:
    """Helper functions for date and time operations"""
    
    @staticmethod
    def get_current_timestamp() -> datetime:
        """Get current UTC timestamp"""
        return datetime.utcnow()
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string"""
        if not dt:
            return ""
        try:
            return dt.strftime(format_str)
        except Exception as e:
            logger.error(f"Error formatting datetime: {str(e)}")
            return str(dt)
    
    @staticmethod
    def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse string to datetime"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, format_str)
        except ValueError as e:
            logger.error(f"Error parsing datetime '{date_str}': {str(e)}")
            return None
    
    @staticmethod
    def get_date_range(days_back: int = 7) -> tuple[datetime, datetime]:
        """Get date range from days_back to now"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date
    
    @staticmethod
    def is_business_hours(dt: datetime = None, start_hour: int = 8, end_hour: int = 18) -> bool:
        """Check if datetime is within business hours"""
        if not dt:
            dt = datetime.utcnow()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if dt.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if it's within business hours
        return start_hour <= dt.hour < end_hour
    
    @staticmethod
    def time_until_business_hours(dt: datetime = None) -> timedelta:
        """Calculate time until next business hours"""
        if not dt:
            dt = datetime.utcnow()
        
        # If it's weekend, calculate time until Monday 8 AM
        if dt.weekday() >= 5:  # Weekend
            days_until_monday = 7 - dt.weekday()
            monday_8am = dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)
            return monday_8am - dt
        
        # If it's before business hours on weekday
        if dt.hour < 8:
            business_start = dt.replace(hour=8, minute=0, second=0, microsecond=0)
            return business_start - dt
        
        # If it's after business hours on weekday
        if dt.hour >= 18:
            next_day_8am = dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return next_day_8am - dt
        
        # Currently in business hours
        return timedelta(0)

class StringHelper:
    """Helper functions for string operations"""
    
    @staticmethod
    def generate_random_string(length: int = 8, include_uppercase: bool = True, 
                             include_lowercase: bool = True, include_digits: bool = True,
                             include_special: bool = False) -> str:
        """Generate a random string with specified characteristics"""
        characters = ""
        if include_uppercase:
            characters += string.ascii_uppercase
        if include_lowercase:
            characters += string.ascii_lowercase
        if include_digits:
            characters += string.digits
        if include_special:
            characters += "!@#$%^&*()_+-="
        
        if not characters:
            characters = string.ascii_letters + string.digits
        
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_visit_code() -> str:
        """Generate a unique visit code"""
        return f"VIS-{DateTimeHelper.get_current_timestamp().strftime('%Y%m%d')}-{StringHelper.generate_random_string(6, include_special=False).upper()}"
    
    @staticmethod
    def generate_reference_number() -> str:
        """Generate a unique reference number"""
        timestamp = int(time.time())
        random_part = StringHelper.generate_random_string(4, include_special=False)
        return f"REF{timestamp}{random_part}".upper()
    
    @staticmethod
    def mask_phone_number(phone: str) -> str:
        """Mask phone number for privacy"""
        if not phone or len(phone) < 4:
            return phone
        
        # Show first 3 and last 3 digits
        if len(phone) <= 6:
            return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]
        else:
            return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for privacy"""
        if not email or "@" not in email:
            return email
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"

class PhoneHelper:
    """Helper functions for phone number operations"""
    
    @staticmethod
    def format_kenyan_phone(phone: str) -> str:
        """Format phone number to Kenyan standard (+254XXXXXXXXX)"""
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Remove leading zeros and handle different formats
        if cleaned.startswith('+254'):
            return cleaned
        elif cleaned.startswith('254'):
            return f"+{cleaned}"
        elif cleaned.startswith('0'):
            return f"+254{cleaned[1:]}"
        elif len(cleaned) == 9 and (cleaned.startswith('7') or cleaned.startswith('1')):
            return f"+254{cleaned}"
        
        return phone  # Return original if format not recognized
    
    @staticmethod
    def is_valid_kenyan_phone(phone: str) -> bool:
        """Check if phone number is valid Kenyan format"""
        formatted = PhoneHelper.format_kenyan_phone(phone)
        
        # Should be +254 followed by 9 digits starting with 7 or 1
        if len(formatted) != 13 or not formatted.startswith('+254'):
            return False
        
        remaining = formatted[4:]  # After +254
        if not remaining.isdigit() or len(remaining) != 9:
            return False
        
        # Should start with 7 (mobile) or 1 (landline)
        return remaining[0] in ['7', '1']

class SecurityHelper:
    """Helper functions for security operations"""
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate a password reset token"""
        return secrets.token_urlsafe(24)
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """Generate a numeric verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: List[str] = None) -> bool:
        """Check if redirect URL is safe"""
        if not url:
            return False
        
        # Don't allow javascript: or data: schemes
        if url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
            return False
        
        # If it's a relative URL, it's safe
        if url.startswith('/'):
            return True
        
        # If allowed hosts are specified, check against them
        if allowed_hosts:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                return parsed.hostname in allowed_hosts
            except Exception:
                return False
        
        return False

class ResponseHelper:
    """Helper functions for API responses"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Success", 
                        status_code: int = 200) -> Dict[str, Any]:
        """Create a standardized success response"""
        response = {
            "success": True,
            "message": message,
            "status_code": status_code,
            "timestamp": DateTimeHelper.get_current_timestamp().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        return response
    
    @staticmethod
    def error_response(message: str = "An error occurred", 
                      status_code: int = 400, error_code: str = None,
                      details: Any = None) -> Dict[str, Any]:
        """Create a standardized error response"""
        response = {
            "success": False,
            "message": message,
            "status_code": status_code,
            "timestamp": DateTimeHelper.get_current_timestamp().isoformat()
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    @staticmethod
    def paginated_response(data: List[Any], total: int, page: int, 
                          limit: int, message: str = "Success") -> Dict[str, Any]:
        """Create a paginated response"""
        total_pages = (total + limit - 1) // limit  # Ceiling division
        
        return {
            "success": True,
            "message": message,
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "timestamp": DateTimeHelper.get_current_timestamp().isoformat()
        }

class DatabaseHelper:
    """Helper functions for database operations"""
    
    @staticmethod
    def get_or_create(db: Session, model, defaults=None, **kwargs):
        """Get an existing instance or create a new one"""
        try:
            instance = db.query(model).filter_by(**kwargs).first()
            if instance:
                return instance, False
            else:
                params = dict(kwargs)
                if defaults:
                    params.update(defaults)
                instance = model(**params)
                db.add(instance)
                db.commit()
                db.refresh(instance)
                return instance, True
        except Exception as e:
            db.rollback()
            logger.error(f"Error in get_or_create: {str(e)}")
            raise
    
    @staticmethod
    def safe_delete(db: Session, instance) -> bool:
        """Safely delete a database instance"""
        try:
            db.delete(instance)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting instance: {str(e)}")
            return False
    
    @staticmethod
    def bulk_insert(db: Session, model, data_list: List[Dict]) -> bool:
        """Bulk insert data"""
        try:
            instances = [model(**data) for data in data_list]
            db.bulk_save_objects(instances)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error in bulk insert: {str(e)}")
            return False

class LoggingHelper:
    """Helper functions for logging"""
    
    @staticmethod
    def log_user_action(user_id: int, action: str, details: Dict = None, 
                       level: str = "INFO"):
        """Log user actions"""
        log_data = {
            "user_id": user_id,
            "action": action,
            "timestamp": DateTimeHelper.get_current_timestamp().isoformat(),
            "details": details or {}
        }
        
        log_message = f"User {user_id} performed action: {action}"
        if details:
            log_message += f" - Details: {json.dumps(details)}"
        
        if level.upper() == "ERROR":
            logger.error(log_message)
        elif level.upper() == "WARNING":
            logger.warning(log_message)
        elif level.upper() == "DEBUG":
            logger.debug(log_message)
        else:
            logger.info(log_message)
    
    @staticmethod
    def log_api_call(endpoint: str, method: str, user_id: int = None, 
                    status_code: int = None, duration: float = None):
        """Log API calls"""
        log_data = {
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "status_code": status_code,
            "duration": duration,
            "timestamp": DateTimeHelper.get_current_timestamp().isoformat()
        }
        
        log_message = f"{method} {endpoint}"
        if user_id:
            log_message += f" (User: {user_id})"
        if status_code:
            log_message += f" - Status: {status_code}"
        if duration:
            log_message += f" - Duration: {duration:.3f}s"
        
        logger.info(log_message)

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator to retry function on exception"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

def measure_execution_time(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f} seconds: {str(e)}")
            raise
    return wrapper

class ConfigHelper:
    """Helper functions for configuration management"""
    
    @staticmethod
    def get_env_var(key: str, default: Any = None, required: bool = False) -> Any:
        """Get environment variable with validation"""
        import os
        
        value = os.getenv(key, default)
        
        if required and value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        
        return value
    
    @staticmethod
    def parse_bool(value: str) -> bool:
        """Parse string to boolean"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        return bool(value)
    
    @staticmethod
    def parse_list(value: str, separator: str = ',') -> List[str]:
        """Parse comma-separated string to list"""
        if not value:
            return []
        
        return [item.strip() for item in value.split(separator) if item.strip()]