from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    VISIT_REQUEST = "visit_request"
    VISIT_APPROVED = "visit_approved"
    VISIT_DENIED = "visit_denied"
    VISITOR_ARRIVAL = "visitor_arrival"
    VISITOR_DEPARTURE = "visitor_departure"
    SECURITY_ALERT = "security_alert"
    SYSTEM_UPDATE = "system_update"
    RESIDENT_APPROVAL = "resident_approval"
    ACCOUNT_STATUS = "account_status"

class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationBase(BaseModel):
    user_id: int
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    data: Optional[Dict[str, Any]] = None
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters')
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Message must be at least 10 characters')
        return v.strip()

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None

class NotificationResponse(NotificationBase):
    id: int
    status: NotificationStatus = NotificationStatus.UNREAD
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificationSearch(BaseModel):
    user_id: Optional[int] = None
    type: Optional[NotificationType] = None
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Limit must be between 1 and 100')
        return v

class BulkNotificationCreate(BaseModel):
    user_ids: list[int]
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    data: Optional[Dict[str, Any]] = None
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one user ID is required')
        if len(v) > 100:
            raise ValueError('Cannot send to more than 100 users at once')
        return v

class NotificationPreferences(BaseModel):
    user_id: int
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    notification_types: Optional[list[NotificationType]] = None
    quiet_hours_start: Optional[str] = None  # Format: "HH:MM"
    quiet_hours_end: Optional[str] = None    # Format: "HH:MM"
    
    @validator('quiet_hours_start', 'quiet_hours_end')
    def validate_time_format(cls, v):
        if v is not None:
            try:
                hour, minute = map(int, v.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError('Invalid time format')
            except:
                raise ValueError('Time must be in HH:MM format')
        return v

class NotificationSummary(BaseModel):
    total_notifications: int
    unread_count: int
    high_priority_count: int
    urgent_count: int
    types_summary: Dict[str, int]

# Template classes for different notification types
class VisitRequestNotificationData(BaseModel):
    visit_request_id: int
    visitor_name: str
    visitor_phone: str
    expected_date: datetime
    purpose_of_visit: str

class VisitApprovalNotificationData(BaseModel):
    visit_request_id: int
    visitor_name: str
    approved: bool
    qr_code: Optional[str] = None
    denial_reason: Optional[str] = None

class VisitorArrivalNotificationData(BaseModel):
    visit_request_id: int
    visitor_name: str
    arrival_time: datetime
    security_personnel: str

class SecurityAlertNotificationData(BaseModel):
    alert_type: str
    visitor_name: Optional[str] = None
    location: Optional[str] = None
    severity: str
    
class NotificationTemplate(BaseModel):
    """Template for creating standardized notifications"""
    
    @staticmethod
    def create_visit_request_notification(
        resident_id: int, 
        visitor_name: str, 
        visit_request_id: int,
        expected_date: datetime,
        purpose: str
    ) -> NotificationCreate:
        return NotificationCreate(
            user_id=resident_id,
            type=NotificationType.VISIT_REQUEST,
            title="New Visit Request",
            message=f"{visitor_name} has requested to visit you on {expected_date.strftime('%Y-%m-%d %H:%M')} for {purpose}",
            priority=NotificationPriority.HIGH,
            data={
                "visit_request_id": visit_request_id,
                "visitor_name": visitor_name,
                "expected_date": expected_date.isoformat(),
                "purpose_of_visit": purpose
            }
        )
    
    @staticmethod
    def create_visit_approval_notification(
        visitor_user_id: int,
        visitor_name: str,
        approved: bool,
        qr_code: Optional[str] = None,
        denial_reason: Optional[str] = None
    ) -> NotificationCreate:
        title = "Visit Approved" if approved else "Visit Denied"
        message = f"Your visit request has been {'approved' if approved else 'denied'}"
        if not approved and denial_reason:
            message += f". Reason: {denial_reason}"
        
        return NotificationCreate(
            user_id=visitor_user_id,
            type=NotificationType.VISIT_APPROVED if approved else NotificationType.VISIT_DENIED,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            data={
                "approved": approved,
                "qr_code": qr_code,
                "denial_reason": denial_reason
            }
        )