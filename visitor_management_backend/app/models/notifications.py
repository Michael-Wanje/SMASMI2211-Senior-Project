from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class NotificationType(str, enum.Enum):
    VISIT_REQUEST = "visit_request"
    VISIT_APPROVED = "visit_approved"
    VISIT_DENIED = "visit_denied"
    VISITOR_ARRIVAL = "visitor_arrival"
    VISITOR_BLACKLISTED = "visitor_blacklisted"
    SYSTEM_ALERT = "system_alert"
    RESIDENT_REGISTRATION = "resident_registration"

class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visit_request_id = Column(Integer, ForeignKey("visit_requests.id"), nullable=True)
    
    # Notification Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    
    # Email Notification
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Data (JSON format for flexibility)
    additional_data = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sender = relationship("User", back_populates="notifications_sent", foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="notifications_received", foreign_keys=[recipient_id])
    visit_request = relationship("VisitRequest", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, recipient_id={self.recipient_id}, type='{self.notification_type}')>"
    
    @property
    def is_expired(self):
        if self.expires_at:
            from datetime import datetime, timezone
            return datetime.now(timezone.utc) > self.expires_at
        return False