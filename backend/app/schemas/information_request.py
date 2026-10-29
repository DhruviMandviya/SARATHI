from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DeficiencyItem(BaseModel):
    id: str
    doc_type: str
    requirement: str
    explanation: Optional[str] = None
    mandatory: bool = True

class InformationRequestCreate(BaseModel):
    title: str
    reason: str
    notice_text: Optional[str] = None
    deadline_days: Optional[int] = 15 # default 15 days if not explicit date
    deadline_date: Optional[datetime] = None # Or explicit deadline date
    deficiencies: List[DeficiencyItem] = Field(default_factory=list)

class InformationRequestOut(BaseModel):
    id: int
    reference_no: str
    application_id: int
    application_no: Optional[str] = None
    institution_id: int
    institution_name: Optional[str] = None
    title: str
    reason: str
    notice_text: Optional[str] = None
    status: str
    issuing_authority: str
    issued_by: int
    issued_at: datetime
    deadline: datetime
    deficiencies: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResponseItemInput(BaseModel):
    deficiency_id: str
    explanation: Optional[str] = None
    document_id: Optional[int] = None
    original_filename: Optional[str] = None
    status: str = "draft" # not_started | draft | completed

class InformationResponseSave(BaseModel):
    items: List[ResponseItemInput] = Field(default_factory=list)

class InformationResponseOut(BaseModel):
    id: int
    request_id: int
    application_id: int
    institution_id: int
    version: int
    status: str
    items: List[Dict[str, Any]]
    submission_receipt: Optional[str] = None
    receipt_no: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InformationRequestDetailOut(BaseModel):
    request: InformationRequestOut
    application_no: str
    institution_name: str
    latest_response: Optional[InformationResponseOut] = None
    response_history: List[InformationResponseOut] = Field(default_factory=list)
    has_released_notice_doc: bool = False

class InformationRequestSummaryCards(BaseModel):
    action_required: int
    response_submitted: int
    under_review: int
    resolved: int
    total: int

class NoticeCandidateItem(BaseModel):
    id: str
    finding_id: Optional[int] = None
    group: str
    category: str
    severity: str
    actionability: str
    is_actionable: bool
    title: str
    doc_type: str
    document_name: str
    explanation: str
    rule_ref: str
    requested_action: str
    requires_explanation: bool
    requires_upload: bool
    status: str

class NoticeCandidatesResponse(BaseModel):
    application_id: int
    application_no: str
    academic_year: str
    institution_name: str
    groups: Dict[str, List[NoticeCandidateItem]]
    summary: Dict[str, int]

class NoticeBuilderSelectedItem(BaseModel):
    finding_id: Optional[int] = None
    title: Optional[str] = None
    category: Optional[str] = "mandatory_compliance"
    doc_type: Optional[str] = "general_compliance"
    requirement: Optional[str] = None
    explanation: str
    requested_action: str
    requires_explanation: bool = True
    requires_upload: bool = False
    mandatory: bool = True

class NoticeBuilderIssueRequest(BaseModel):
    remarks: Optional[str] = None
    official_remarks: Optional[str] = None
    notice_text: Optional[str] = None
    deadline_days: Optional[int] = 15
    cure_period_days: Optional[int] = None
    deadline_date: Optional[datetime] = None
    selected_items: List[NoticeBuilderSelectedItem] = Field(default_factory=list)
