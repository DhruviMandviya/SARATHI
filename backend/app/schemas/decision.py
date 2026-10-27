from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DecisionCreate(BaseModel):
    outcome: str = Field(..., description="approved | rejected | info_requested")
    remarks: str = Field(..., min_length=5, description="Mandatory official justification remarks")

class DecisionOut(BaseModel):
    id: int
    application_id: int
    official_id: int
    outcome: str
    remarks: str
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DeficiencyLetterUpdate(BaseModel):
    edited_text: str
    status: Optional[str] = "draft" # draft or sent

class DeficiencyLetterOut(BaseModel):
    id: int
    application_id: int
    draft_text: str
    edited_text: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
