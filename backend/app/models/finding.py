from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    related_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    category = Column(String(50), nullable=False) # missing, expired, incomplete, mismatch, duplicate, tampering, metadata, verification, compliance, quality
    severity = Column(String(20), nullable=False) # critical, warning, info
    title = Column(String(255), nullable=False)
    explanation = Column(String(1000), nullable=False)
    evidence = Column(JSON, default=dict, nullable=False) # {document_name, page, extracted_values, matched_signals, ...}
    bbox = Column(JSON, default=dict, nullable=True) # {"x": .., "y": .., "width": .., "height": ..}
    confidence = Column(Float, default=1.0, nullable=False)
    confidence_meaning = Column(String(255), nullable=False) # deterministic check, heuristic signal strength, etc.
    rule_ref = Column(String(100), nullable=True) # e.g. Rule 4.1.2 or consistency_check_name
    status = Column(String(30), default="open", nullable=False) # open, acknowledged, dismissed
    dismissed_reason = Column(String(500), nullable=True)
    dismissed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application", back_populates="flags")
    document = relationship("Document", foreign_keys=[document_id], back_populates="flags")
    related_document = relationship("Document", foreign_keys=[related_document_id])
