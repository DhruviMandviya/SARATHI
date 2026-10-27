from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VerificationResultOut(BaseModel):
    id: int
    document_id: int
    authority: str
    adapter_name: str
    reference_no: Optional[str] = None
    status: str
    is_simulated: bool
    raw_response: Dict[str, Any]
    message: Optional[str] = None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)
