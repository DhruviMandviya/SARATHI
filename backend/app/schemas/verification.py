from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VerificationResultOut(BaseModel):
    id: int
    document_id: int
    authority: str
    adapter_name: str
    reference_no: Optional[str] = None
    checked_reference: Optional[str] = None
    status: str
    is_simulated: bool
    verification_mode: Optional[str] = "SIMULATED"
    manual_remarks: Optional[str] = None
    manual_verified_by: Optional[int] = None
    manual_reference_no: Optional[str] = None
    ocr_reference_no: Optional[str] = None
    raw_response: Dict[str, Any]
    message: Optional[str] = None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecordManualVerificationRequest(BaseModel):
    outcome: str # verified, not_verified, unable_to_verify
    remarks: str
    evidence_reviewed: Optional[str] = None
    manual_reference_no: Optional[str] = None
