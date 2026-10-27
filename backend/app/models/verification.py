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
    status = Column(String(50), default="pending", nullable=False) # verified, in_progress, not_verified, pending
    is_simulated = Column(Boolean, default=True, nullable=False) # ALWAYS TRUE for MVP
    raw_response = Column(JSON, default=dict, nullable=False)
    message = Column(String(500), nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="verification_results")
