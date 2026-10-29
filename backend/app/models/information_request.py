from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class InformationRequest(Base):
    __tablename__ = "information_requests"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(50), unique=True, index=True, nullable=False) # e.g. NOT-2026-XXXXX
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    notice_text = Column(Text, nullable=True)
    status = Column(String(50), default="action_required", nullable=False, index=True)
    # draft | action_required | submitted | under_review | further_info_required | resolved

    issuing_authority = Column(String(255), default="AICTE Scrutiny Committee", nullable=False)
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deadline = Column(DateTime, nullable=False) # Stored actual deadline from notice

    # Structured list of deficiency items:
    # [{"id": "def-1", "doc_type": "fire_noc", "requirement": "...", "explanation": "...", "mandatory": True}]
    deficiencies = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application")
    institution = relationship("Institution")
    issuer = relationship("User")
    responses = relationship("InformationResponse", back_populates="request", cascade="all, delete-orphan")

class InformationResponse(Base):
    __tablename__ = "information_responses"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("information_requests.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    
    version = Column(Integer, default=1, nullable=False) # Preserves submitted response history
    status = Column(String(50), default="draft", nullable=False) # draft | submitted
    
    # Structured response items per deficiency:
    # [{"deficiency_id": "def-1", "explanation": "...", "document_id": 10, "original_filename": "...", "status": "completed"}]
    items = Column(JSON, default=list, nullable=False)
    
    submission_receipt = Column(String(100), nullable=True) # e.g. RCP-2026-XXXXX
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    request = relationship("InformationRequest", back_populates="responses")
    application = relationship("Application")
    institution = relationship("Institution")
    submitter = relationship("User")
