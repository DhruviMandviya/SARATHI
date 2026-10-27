from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class FlagOut(BaseModel):
    id: int
    application_id: int
    document_id: Optional[int] = None
    related_document_id: Optional[int] = None
    category: str
    severity: str
    title: str
    explanation: str
    evidence: Dict[str, Any]
    bbox: Optional[Dict[str, Any]] = None
    confidence: float
    confidence_meaning: str
    rule_ref: Optional[str] = None
    status: str
    dismissed_reason: Optional[str] = None
    dismissed_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FlagAcknowledge(BaseModel):
    status: str # acknowledged or dismissed
    reason: Optional[str] = None
