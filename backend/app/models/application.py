from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    application_no = Column(String(50), unique=True, index=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    type = Column(String(100), default="New Technical Institution", nullable=False)
    academic_year = Column(String(20), default="2026-2027", nullable=False)
    status = Column(String(50), default="draft", nullable=False) 
    # draft | submitted | processing | under_verification | needs_review | info_requested | approved | rejected
    
    risk_score = Column(Float, default=0.0, nullable=False)
    risk_band = Column(String(20), default="Low", nullable=False) # Low | Medium | High
    risk_breakdown = Column(JSON, default=dict, nullable=False)
    declared_details = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    institution = relationship("Institution", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="application", cascade="all, delete-orphan")
    compliance_results = relationship("ComplianceResult", back_populates="application", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="application", cascade="all, delete-orphan")
    deficiency_letters = relationship("DeficiencyLetter", back_populates="application", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    application_type = Column(String(100), default="New Technical Institution", nullable=False)
    doc_type = Column(String(100), nullable=False)
    mandatory = Column(Integer, default=1, nullable=False) # 1 = mandatory, 0 = optional
    validity_required = Column(Integer, default=0, nullable=False)
    description = Column(String(500), nullable=False)
