from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class VisitStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EntryType(str, enum.Enum):
    PRE_REGISTERED = "pre_registered"
    WALK_IN = "walk_in"
    RESIDENT_REGISTERED = "resident_registered"

class VisitRequest(Base):
    __tablename__ = "visit_requests"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    security_personnel_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Visit Details
    purpose_of_visit = Column(Text, nullable=False)
    visit_date = Column(DateTime(timezone=True), nullable=False)
    expected_duration = Column(Integer, nullable=True)  # in minutes
    
    # Status and Type
    status = Column(Enum(VisitStatus), default=VisitStatus.PENDING, nullable=False)
    entry_type = Column(Enum(EntryType), nullable=False)
    
    # Entry/Exit Times
    actual_entry_time = Column(DateTime(timezone=True), nullable=True)
    actual_exit_time = Column(DateTime(timezone=True), nullable=True)
    
    # Approval/Denial Details
    approved_at = Column(DateTime(timezone=True), nullable=True)
    denied_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)
    
    # Additional Information
    special_instructions = Column(Text, nullable=True)
    vehicle_registration = Column(String(20), nullable=True)
    number_of_guests = Column(Integer, default=1, nullable=False)
    
    # Security Verification
    id_verified = Column(Boolean, default=False, nullable=False)
    security_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    visitor = relationship("Visitor", back_populates="visit_requests")
    resident = relationship("User", back_populates="visit_requests_as_resident", foreign_keys=[resident_id])
    security_personnel = relationship("User", back_populates="visit_requests_as_security", foreign_keys=[security_personnel_id])
    notifications = relationship("Notification", back_populates="visit_request")
    
    def __repr__(self):
        return f"<VisitRequest(id={self.id}, visitor_id={self.visitor_id}, status='{self.status}')>"
    
    @property
    def is_active(self):
        return self.status in [VisitStatus.PENDING, VisitStatus.APPROVED]
    
    @property
    def duration_minutes(self):
        if self.actual_entry_time and self.actual_exit_time:
            delta = self.actual_exit_time - self.actual_entry_time
            return int(delta.total_seconds() / 60)
        return None