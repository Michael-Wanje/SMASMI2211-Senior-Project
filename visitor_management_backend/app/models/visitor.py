from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Visitor(Base):
    __tablename__ = "visitors"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Personal Information
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    id_number = Column(String(50), nullable=True)
    
    # Additional Details
    company = Column(String(255), nullable=True)
    purpose_of_visit = Column(Text, nullable=True)
    vehicle_registration = Column(String(20), nullable=True)
    
    # Status
    is_blacklisted = Column(Boolean, default=False, nullable=False)
    blacklist_reason = Column(Text, nullable=True)
    blacklisted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    visit_requests = relationship("VisitRequest", back_populates="visitor")
    blacklist_entries = relationship("Blacklist", back_populates="visitor")
    
    def __repr__(self):
        return f"<Visitor(id={self.id}, name='{self.full_name}', phone='{self.phone_number}')>"
    
    @property
    def is_blocked(self):
        return self.is_blacklisted