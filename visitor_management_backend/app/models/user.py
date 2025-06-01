from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserType(str, enum.Enum):
    ADMIN = "admin"
    RESIDENT = "resident"
    SECURITY = "security"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    
    # Profile information
    apartment_number = Column(String(20), nullable=True)  # For residents
    id_number = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    # Status fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)  # For resident approval
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    visit_requests_as_resident = relationship("VisitRequest", back_populates="resident", foreign_keys="VisitRequest.resident_id")
    visit_requests_as_security = relationship("VisitRequest", back_populates="security_personnel", foreign_keys="VisitRequest.security_personnel_id")
    notifications_sent = relationship("Notification", back_populates="sender", foreign_keys="Notification.sender_id")
    notifications_received = relationship("Notification", back_populates="recipient", foreign_keys="Notification.recipient_id")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', user_type='{self.user_type}')>"
    
    @property
    def is_admin(self):
        return self.user_type == UserType.ADMIN
    
    @property
    def is_resident(self):
        return self.user_type == UserType.RESIDENT
    
    @property
    def is_security(self):
        return self.user_type == UserType.SECURITY