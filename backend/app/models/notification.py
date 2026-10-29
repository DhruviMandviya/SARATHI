from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role = Column(String(50), nullable=True, index=True) # e.g. "official", "institution", "admin"
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False) 
    # notice_issued, response_submitted, further_info_requested, request_resolved, decision_recorded, action_required
    
    link = Column(String(255), nullable=True) # route/URL to navigate to
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    reference_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User")
    institution = relationship("Institution")
    application = relationship("Application")
