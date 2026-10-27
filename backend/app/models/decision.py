from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    official_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String(50), nullable=False) # approved, rejected, info_requested
    remarks = Column(Text, nullable=False)
    decided_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application", back_populates="decisions")
    official = relationship("User")

class DeficiencyLetter(Base):
    __tablename__ = "deficiency_letters"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    draft_text = Column(Text, nullable=False)
    edited_text = Column(Text, nullable=True)
    status = Column(String(50), default="draft", nullable=False) # draft, sent
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application", back_populates="deficiency_letters")
    creator = relationship("User")
