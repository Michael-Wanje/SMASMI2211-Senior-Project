from pydantic import BaseModel, validator, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class VisitorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"

class VisitorBase(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    id_number: Optional[str] = None
    company: Optional[str] = None
    purpose_of_visit: str
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        return v.strip().title()
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Remove any spaces or special characters
        phone = ''.join(filter(str.isdigit, v))
        if len(phone) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return phone
    
    @validator('purpose_of_visit')
    def validate_purpose(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Purpose of visit must be at least 3 characters')
        return v.strip()

class VisitorCreate(VisitorBase):
    pass

class VisitorUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    id_number: Optional[str] = None
    company: Optional[str] = None
    purpose_of_visit: Optional[str] = None

class VisitorResponse(VisitorBase):
    id: int
    status: VisitorStatus
    qr_code: Optional[str] = None
    is_blacklisted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class VisitorRegistration(BaseModel):
    visitor: VisitorCreate
    resident_id: int
    expected_date: datetime
    expected_duration_hours: Optional[int] = 2
    additional_notes: Optional[str] = None
    
    @validator('expected_date')
    def validate_expected_date(cls, v):
        if v < datetime.now():
            raise ValueError('Expected date cannot be in the past')
        return v
    
    @validator('expected_duration_hours')
    def validate_duration(cls, v):
        if v is not None and (v < 1 or v > 24):
            raise ValueError('Duration must be between 1 and 24 hours')
        return v

class VisitorSearchParams(BaseModel):
    search_term: Optional[str] = None
    status: Optional[VisitorStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    resident_id: Optional[int] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Limit must be between 1 and 100')
        return v

class VisitorCheckIn(BaseModel):
    visitor_id: int
    security_personnel_id: int
    actual_arrival_time: Optional[datetime] = None
    notes: Optional[str] = None

class VisitorCheckOut(BaseModel):
    visitor_id: int
    security_personnel_id: int
    actual_departure_time: Optional[datetime] = None
    notes: Optional[str] = None

class BlacklistEntry(BaseModel):
    visitor_id: int
    resident_id: int
    reason: str
    blacklisted_by: int  # User ID who blacklisted
    
    @validator('reason')
    def validate_reason(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError('Blacklist reason must be at least 5 characters')
        return v.strip()

class BlacklistResponse(BaseModel):
    id: int
    visitor_id: int
    resident_id: int
    reason: str
    blacklisted_by: int
    blacklisted_at: datetime
    visitor: VisitorResponse
    
    class Config:
        from_attributes = True