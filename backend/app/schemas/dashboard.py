from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class StatusCount(BaseModel):
    status: str
    count: int
    percentage: float = 0.0

class RecentAlert(BaseModel):
    id: int
    application_id: int
    application_no: str
    institution_name: str
    title: str
    severity: str
    category: str
    created_at: str
    affected_document: Optional[str] = "Document"
    review_status: str = "open"
    finding_group: str = "deficiencies" # deficiencies | mismatches | duplicates | forensics

class HighRiskApp(BaseModel):
    id: int
    application_no: str
    institution_name: str
    state: str
    risk_score: float
    risk_band: str
    status: str
    critical_flags_count: int
    reasons: List[str] = Field(default_factory=list)
    submission_date: Optional[str] = None
    unresolved_flags_count: int = 0

class ProcessingStats(BaseModel):
    avg_processing_time_sec: float
    total_processed_documents: int
    ocr_success_rate: float
    native_pdf_count: int = 0
    native_pdf_success_rate: float = 0.0
    ocr_count: int = 0
    ocr_rate: float = 0.0
    pending_jobs: int = 0
    failed_jobs: int = 0
    reporting_period: str = "Cycle 2026-2027"
    last_refresh_time: str = ""
    service_health: str = "Healthy"

class DashboardSummary(BaseModel):
    total_applications: int
    draft: int = 0
    submitted: int = 0
    under_verification: int
    needs_review: int
    approved: int
    rejected: int
    info_requested: int
    status_distribution: List[StatusCount]
    recent_alerts: List[RecentAlert]
    high_risk_applications: List[HighRiskApp]
    processing_stats: ProcessingStats
