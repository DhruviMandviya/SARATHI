from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ExtractedFieldOut(BaseModel):
    id: int
    document_id: int
    key: str
    value: Optional[str] = None
    ocr_confidence: float
    extraction_method: str
    page: int
    bbox: Dict[str, Any]
    needs_review: bool
    edited_by: Optional[int] = None
    edited_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class FieldUpdate(BaseModel):
    value: str
    remarks: Optional[str] = None

class OfficialDocumentReviewRequest(BaseModel):
    outcome: str # verified, mismatch_confirmed, unable_to_verify, pending_review
    remarks: Optional[str] = None
    field_name: Optional[str] = None

class DocumentOut(BaseModel):
    id: int
    application_id: int
    doc_type: str
    original_filename: str
    stored_path: str
    mime_type: str
    size: int
    sha256: Optional[str] = None
    phash: Optional[str] = None
    page_count: int
    processing_status: str
    processing_stage: str
    processing_error: Optional[str] = None
    validation_status: str
    official_verification_status: Optional[str] = "pending_review"
    official_verification_remarks: Optional[str] = None
    official_verified_by: Optional[int] = None
    official_verified_at: Optional[datetime] = None
    uploaded_at: datetime
    superseded_by: Optional[int] = None
    extracted_fields: List[ExtractedFieldOut] = []

    model_config = ConfigDict(from_attributes=True)
