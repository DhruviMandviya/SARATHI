from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    authority = Column(String(200), nullable=False) # e.g. Municipal Building Authority, Registrar of Societies
    adapter_name = Column(String(100), nullable=False)
    reference_no = Column(String(100), nullable=True)
    status = Column(String(50), default="pending", nullable=False) # verified, in_progress, not_verified, pending, unable_to_verify, manual_verified
    is_simulated = Column(Boolean, default=True, nullable=False) # True if from mock adapter, False if manual officer review
    verification_mode = Column(String(30), default="SIMULATED", nullable=False) # SIMULATED, LIVE, MANUAL
    manual_remarks = Column(String(500), nullable=True)
    manual_verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    manual_reference_no = Column(String(100), nullable=True)
    ocr_reference_no = Column(String(100), nullable=True)
    raw_response = Column(JSON, default=dict, nullable=False)
    message = Column(String(500), nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="verification_results")
    manual_verifier = relationship("User", foreign_keys=[manual_verified_by])
