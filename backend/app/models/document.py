from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    doc_type = Column(String(100), nullable=False)  # land_document, building_plan, fire_noc, society_registration, etc.
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False) # bytes
    sha256 = Column(String(64), nullable=True, index=True)
    phash = Column(String(64), nullable=True, index=True)
    page_count = Column(Integer, default=1, nullable=False)

    processing_status = Column(String(50), default="queued", nullable=False) # queued, processing, completed, failed
    processing_stage = Column(String(100), default="Queued", nullable=False)
    processing_error = Column(String(1000), nullable=True)

    validation_status = Column(String(50), default="valid", nullable=False) # valid, incomplete, expired, mismatch, missing
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    superseded_by = Column(Integer, ForeignKey("documents.id"), nullable=True)

    application = relationship("Application", back_populates="documents")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="document", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="document", cascade="all, delete-orphan", foreign_keys="Flag.document_id")

class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    key = Column(String(100), nullable=False, index=True)
    value = Column(String(500), nullable=True)
    ocr_confidence = Column(Float, default=1.0, nullable=False)
    extraction_method = Column(String(50), default="regex", nullable=False) # text_layer, tesseract, regex, rule
    page = Column(Integer, default=1, nullable=False)
    bbox = Column(JSON, default=dict, nullable=False) # {"x": .., "y": .., "width": .., "height": ..}
    needs_review = Column(Boolean, default=False, nullable=False)
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    edited_value = Column(String(500), nullable=True)

    document = relationship("Document", back_populates="extracted_fields")
