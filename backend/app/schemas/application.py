from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DeclaredDetails(BaseModel):
    institution_name: Optional[str] = None
    trust_name: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    land_area_acres: Optional[float] = None
    built_up_area_sqm: Optional[float] = None
    student_intake: Optional[int] = None
    faculty_count: Optional[int] = None
    student_faculty_ratio: Optional[float] = None
    labs_count: Optional[int] = None
    ews_quota_percentage: Optional[float] = None
    corpus_fund_lakhs: Optional[float] = None
    affidavit_stamp_value_inr: Optional[float] = None
    extra_details: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ApplicationCreate(BaseModel):
    type: str = "New Technical Institution"
    academic_year: str = "2026-2027"
    declared_details: Optional[DeclaredDetails] = None

class ChecklistItemOut(BaseModel):
    id: int
    application_type: str
    doc_type: str
    mandatory: int
    validity_required: int
    description: str

    model_config = ConfigDict(from_attributes=True)

class ApplicationOut(BaseModel):
    id: int
    application_no: str
    institution_id: int
    type: str
    academic_year: str
    status: str
    risk_score: float
    risk_band: str
    risk_breakdown: Dict[str, Any]
    declared_details: Dict[str, Any]
    created_at: datetime
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
