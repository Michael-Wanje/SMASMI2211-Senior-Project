from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Blacklist(Base):
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blacklisted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Blacklist Details
    reason = Column(Text, nullable=False)
    is_permanent = Column(Boolean, default=True, nullable=False)
    
    # Temporary blacklist (if not permanent)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    removed_at = Column(DateTime(timezone=True), nullable=True)
    removed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    removal_reason = Column(Text, nullable=True)
    
    # Relationships
    visitor = relationship("Visitor", back_populates="blacklist_entries")
    resident = relationship("User", foreign_keys=[resident_id])
    blacklisted_by_user = relationship("User", foreign_keys=[blacklisted_by])
    removed_by_user = relationship("User", foreign_keys=[removed_by])
    
    def __repr__(self):
        return f"<Blacklist(id={self.id}, visitor_id={self.visitor_id}, resident_id={self.resident_id})>"
    
    @property
    def is_expired(self):
        if not self.is_permanent and self.expires_at:
            from datetime import datetime, timezone
            return datetime.now(timezone.utc) > self.expires_at
        return False
    
    @property
    def is_valid(self):
        return self.is_active and not self.is_expired