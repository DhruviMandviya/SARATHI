from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, verify_institution_access
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.compliance import ComplianceResult
from backend.app.schemas.compliance import ComplianceResultOut
from backend.app.engines.compliance import ComplianceEngine

router = APIRouter(tags=["Compliance Checking"])

@router.get("/applications/{application_id}/compliance", response_model=List[ComplianceResultOut])
def get_application_compliance(
    application_id: int,
    re_evaluate: bool = Query(False, description="Force re-evaluation of rules"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    if re_evaluate and current_user.role not in ("official", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorised officials may trigger compliance re-evaluation."
        )

    existing = db.query(ComplianceResult).filter(ComplianceResult.application_id == application_id).all()

    if not existing or re_evaluate:
        engine = ComplianceEngine(db)
        results = engine.evaluate_application(application_id)
        return results

    return existing
