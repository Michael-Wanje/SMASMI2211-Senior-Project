from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RequestType(str, Enum):
    PRE_REGISTERED = "pre_registered"      # Visitor registered in advance
    WALK_IN = "walk_in"                    # Visitor arrived without registration
    RESIDENT_INVITED = "resident_invited"  # Resident registered visitor directly

class VisitRequestBase(BaseModel):
    visitor_id: int
    resident_id: int
    request_type: RequestType
    expected_date: datetime
    expected_duration_hours: Optional[int] = 2
    purpose_of_visit: str
    additional_notes: Optional[str] = None
    
    @validator('expected_date')
    def validate_expected_date(cls, v):
        # Allow past dates for walk-in requests
        return v
    
    @validator('expected_duration_hours')
    def validate_duration(cls, v):
        if v is not None and (v < 1 or v > 24):
            raise ValueError('Duration must be between 1 and 24 hours')
        return v
    
    @validator('purpose_of_visit')
    def validate_purpose(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Purpose of visit must be at least 3 characters')
        return v.strip()

class VisitRequestCreate(VisitRequestBase):
    pass

class VisitRequestUpdate(BaseModel):
    expected_date: Optional[datetime] = None
    expected_duration_hours: Optional[int] = None
    purpose_of_visit: Optional[str] = None
    additional_notes: Optional[str] = None

class VisitRequestResponse(VisitRequestBase):
    id: int
    status: RequestStatus
    qr_code: Optional[str] = None
    actual_arrival_time: Optional[datetime] = None
    actual_departure_time: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    denied_reason: Optional[str] = None
    security_personnel_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    visitor: Optional[dict] = None
    resident: Optional[dict] = None
    approver: Optional[dict] = None
    security_personnel: Optional[dict] = None
    
    class Config:
        from_attributes = True

class VisitRequestApproval(BaseModel):
    request_id: int
    approved: bool
    denial_reason: Optional[str] = None
    approved_by: int
    
    @validator('denial_reason')
    def validate_denial_reason(cls, v, values):
        if not values.get('approved') and not v:
            raise ValueError('Denial reason is required when rejecting a request')
        return v

class VisitRequestSearch(BaseModel):
    status: Optional[RequestStatus] = None
    request_type: Optional[RequestType] = None
    resident_id: Optional[int] = None
    visitor_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_term: Optional[str] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Limit must be between 1 and 100')
        return v

class WalkInRequest(BaseModel):
    visitor_name: str
    visitor_phone: str
    visitor_email: Optional[str] = None
    visitor_id_number: Optional[str] = None
    visitor_company: Optional[str] = None
    resident_id: int
    purpose_of_visit: str
    security_personnel_id: int
    additional_notes: Optional[str] = None
    
    @validator('visitor_name')
    def validate_visitor_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Visitor name must be at least 2 characters')
        return v.strip().title()
    
    @validator('visitor_phone')
    def validate_visitor_phone(cls, v):
        phone = ''.join(filter(str.isdigit, v))
        if len(phone) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return phone

class ResidentInvitation(BaseModel):
    visitor_name: str
    visitor_phone: str
    visitor_email: Optional[str] = None
    visitor_id_number: Optional[str] = None
    visitor_company: Optional[str] = None
    expected_date: datetime
    expected_duration_hours: Optional[int] = 2
    purpose_of_visit: str
    additional_notes: Optional[str] = None
    
    @validator('expected_date')
    def validate_expected_date(cls, v):
        if v < datetime.now():
            raise ValueError('Expected date cannot be in the past')
        return v

class CheckInOut(BaseModel):
    request_id: int
    security_personnel_id: int
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None

class VisitSummary(BaseModel):
    total_requests: int
    pending_requests: int
    approved_requests: int
    denied_requests: int
    completed_visits: int
    active_visitors: int  # Currently checked in
    
class DailyVisitReport(BaseModel):
    date: str
    total_visits: int
    approved_visits: int
    denied_visits: int
    walk_in_visits: int
    pre_registered_visits: int
    resident_invited_visits: int
    average_duration: Optional[float] = None
    peak_hours: Optional[dict] = None