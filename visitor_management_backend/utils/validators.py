import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator

# Phone number validator
def validate_phone_number(phone_number):
    """
    Validate phone number format
    Accepts formats: +254XXXXXXXXX, 07XXXXXXXX, 01XXXXXXXX
    """
    # Remove spaces and special characters except +
    cleaned_phone = re.sub(r'[^\d+]', '', phone_number)
    
    # Kenyan phone number patterns
    patterns = [
        r'^\+254[17]\d{8}$',  # +254 format
        r'^07\d{8}$',         # 07 format
        r'^01\d{8}$',         # 01 format
    ]
    
    if not any(re.match(pattern, cleaned_phone) for pattern in patterns):
        raise ValidationError(
            _('Enter a valid phone number. Examples: +254712345678, 0712345678, 0112345678'),
            code='invalid_phone'
        )

def validate_national_id(national_id):
    """
    Validate Kenyan national ID format
    Should be 8 digits
    """
    if not re.match(r'^\d{8}$', str(national_id)):
        raise ValidationError(
            _('National ID must be exactly 8 digits'),
            code='invalid_national_id'
        )

def validate_apartment_number(apartment_number):
    """
    Validate apartment number format
    Should be alphanumeric and between 1-10 characters
    """
    if not re.match(r'^[A-Za-z0-9]{1,10}$', apartment_number):
        raise ValidationError(
            _('Apartment number must be alphanumeric and between 1-10 characters'),
            code='invalid_apartment'
        )

def validate_strong_password(password):
    """
    Validate password strength
    Must contain: uppercase, lowercase, digit, special character
    Minimum 8 characters
    """
    if len(password) < 8:
        raise ValidationError(
            _('Password must be at least 8 characters long'),
            code='password_too_short'
        )
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(
            _('Password must contain at least one uppercase letter'),
            code='password_no_uppercase'
        )
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(
            _('Password must contain at least one lowercase letter'),
            code='password_no_lowercase'
        )
    
    if not re.search(r'[0-9]', password):
        raise ValidationError(
            _('Password must contain at least one digit'),
            code='password_no_digit'
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(
            _('Password must contain at least one special character'),
            code='password_no_special'
        )

def validate_email_domain(email):
    """
    Validate email domain (optional - can be customized for specific domains)
    """
    allowed_domains = [
        'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
        'icloud.com', 'company.com'  # Add your company domain
    ]
    
    domain = email.split('@')[1].lower()
    
    # For now, we'll allow all domains, but you can uncomment below to restrict
    # if domain not in allowed_domains:
    #     raise ValidationError(
    #         _('Email domain not allowed. Please use a valid email address'),
    #         code='invalid_email_domain'
    #     )

def validate_visit_purpose(purpose):
    """
    Validate visit purpose
    Should not be empty and should be reasonable length
    """
    if len(purpose.strip()) < 3:
        raise ValidationError(
            _('Visit purpose must be at least 3 characters long'),
            code='purpose_too_short'
        )
    
    if len(purpose) > 200:
        raise ValidationError(
            _('Visit purpose cannot exceed 200 characters'),
            code='purpose_too_long'
        )
    
    # Check for inappropriate content (basic check)
    inappropriate_words = ['test', 'xxx', 'spam']  # Add more as needed
    if any(word in purpose.lower() for word in inappropriate_words):
        raise ValidationError(
            _('Visit purpose contains inappropriate content'),
            code='inappropriate_purpose'
        )

def validate_future_date(date):
    """
    Validate that date is not in the past
    """
    from django.utils import timezone
    from datetime import date as date_type
    
    if isinstance(date, date_type):
        today = timezone.now().date()
    else:
        today = timezone.now()
    
    if date < today:
        raise ValidationError(
            _('Date cannot be in the past'),
            code='past_date'
        )

def validate_business_hours(time):
    """
    Validate that time is within business hours (6 AM to 10 PM)
    """
    from datetime import time as time_type
    
    start_time = time_type(6, 0)  # 6:00 AM
    end_time = time_type(22, 0)   # 10:00 PM
    
    if not (start_time <= time <= end_time):
        raise ValidationError(
            _('Visit time must be between 6:00 AM and 10:00 PM'),
            code='outside_business_hours'
        )

def validate_file_size(file):
    """
    Validate uploaded file size (max 5MB)
    """
    max_size = 5 * 1024 * 1024  # 5MB
    
    if file.size > max_size:
        raise ValidationError(
            _('File size cannot exceed 5MB'),
            code='file_too_large'
        )

def validate_image_file(file):
    """
    Validate that uploaded file is an image
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    
    if not any(file.name.lower().endswith(ext) for ext in allowed_extensions):
        raise ValidationError(
            _('Only image files are allowed (JPG, PNG, GIF, BMP)'),
            code='invalid_image_format'
        )

def validate_no_special_characters_in_name(name):
    """
    Validate that name contains only letters, spaces, and common punctuation
    """
    if not re.match(r'^[a-zA-Z\s\.\-\']+$', name):
        raise ValidationError(
            _('Name can only contain letters, spaces, dots, hyphens, and apostrophes'),
            code='invalid_name_characters'
        )

def validate_minimum_age(birth_date):
    """
    Validate minimum age (18 years)
    """
    from datetime import date
    from dateutil import relativedelta
    
    today = date.today()
    age = relativedelta.relativedelta(today, birth_date).years
    
    if age < 18:
        raise ValidationError(
            _('User must be at least 18 years old'),
            code='minimum_age_required'
        )

# Custom regex validators for common fields
phone_validator = RegexValidator(
    regex=r'^\+?254[17]\d{8}$|^07\d{8}$|^01\d{8}$',
    message=_('Enter a valid phone number'),
    code='invalid_phone'
)

national_id_validator = RegexValidator(
    regex=r'^\d{8}$',
    message=_('National ID must be exactly 8 digits'),
    code='invalid_national_id'
)

apartment_validator = RegexValidator(
    regex=r'^[A-Za-z0-9]{1,10}$',
    message=_('Apartment number must be alphanumeric (1-10 characters)'),
    code='invalid_apartment'
)

name_validator = RegexValidator(
    regex=r'^[a-zA-Z\s\.\-\']+$',
    message=_('Name can only contain letters, spaces, dots, hyphens, and apostrophes'),
    code='invalid_name'
)

def validate_unique_visitor_per_resident(visitor_phone, resident, visit_date):
    """
    Validate that a visitor doesn't have multiple pending requests for the same resident
    """
    from apps.visitors.models import VisitRequest, Visitor
    
    try:
        visitor = Visitor.objects.get(phone_number=visitor_phone)
        existing_requests = VisitRequest.objects.filter(
            visitor=visitor,
            resident=resident,
            status='pending',
            visit_date=visit_date
        )
        
        if existing_requests.exists():
            raise ValidationError(
                _('You already have a pending visit request for this resident on this date'),
                code='duplicate_request'
            )
    except Visitor.DoesNotExist:
        pass  # New visitor, no validation needed

def validate_not_blacklisted(visitor_phone, resident):
    """
    Validate that visitor is not blacklisted by the resident
    """
    from apps.visitors.models import Visitor
    
    try:
        visitor = Visitor.objects.get(phone_number=visitor_phone)
        if visitor.is_blacklisted:
            raise ValidationError(
                _('You are restricted from making visit requests'),
                code='visitor_blacklisted'
            )
    except Visitor.DoesNotExist:
        pass  # New visitor, no validation needed