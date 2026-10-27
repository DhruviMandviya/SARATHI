from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class StatusCount(BaseModel):
    status: str
    count: int

class RecentAlert(BaseModel):
    id: int
    application_id: int
    application_no: str
    institution_name: str
    title: str
    severity: str
    category: str
    created_at: str

class HighRiskApp(BaseModel):
    id: int
    application_no: str
    institution_name: str
    state: str
    risk_score: float
    risk_band: str
    status: str
    critical_flags_count: int

class ProcessingStats(BaseModel):
    avg_processing_time_sec: float
    total_processed_documents: int
    ocr_success_rate: float

class DashboardSummary(BaseModel):
    total_applications: int
    under_verification: int
    needs_review: int
    approved: int
    rejected: int
    info_requested: int
    status_distribution: List[StatusCount]
    recent_alerts: List[RecentAlert]
    high_risk_applications: List[HighRiskApp]
    processing_stats: ProcessingStats
