from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, require_official, verify_institution_access
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.decision import Decision
from backend.app.schemas.decision import DecisionCreate, DecisionOut
from backend.app.services.audit import record_audit_event

router = APIRouter(tags=["Official Decisions"])

@router.post("/applications/{application_id}/decision", response_model=DecisionOut)
def record_application_decision(
    application_id: int,
    payload: DecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Records an official scrutiny committee decision.
    Strictly enforced: The AI recommends; the authorised official decides.
    Mandatory remarks required. Appends immutable audit record.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    valid_outcomes = ["approved", "rejected", "info_requested"]
    if payload.outcome.lower() not in valid_outcomes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision outcome '{payload.outcome}'. Must be one of: {valid_outcomes}"
        )

    remarks = payload.remarks.strip()
    if len(remarks) < 5:
        raise HTTPException(
            status_code=400,
            detail="Mandatory scrutiny remarks must contain at least 5 characters of substantive rationale."
        )

    old_status = app.status
    app.status = payload.outcome.lower()

    # Create or update Decision record
    decision = db.query(Decision).filter(Decision.application_id == application_id).first()
    if decision:
        decision.outcome = payload.outcome.lower()
        decision.remarks = remarks
        decision.official_id = current_user.id
        decision.decided_at = datetime.now(timezone.utc)
    else:
        decision = Decision(
            application_id=app.id,
            official_id=current_user.id,
            outcome=payload.outcome.lower(),
            remarks=remarks,
            decided_at=datetime.now(timezone.utc)
        )
        db.add(decision)

    # If outcome is INFO_REQUESTED, persist the formal statutory notice in information_requests
    from backend.app.models.information_request import InformationRequest
    from backend.app.services.notice_sync import persist_official_notice_for_application
    from backend.app.services.notification import notify_institution

    if payload.outcome.lower() == "info_requested":
        req = persist_official_notice_for_application(
            app=app,
            official_id=current_user.id,
            remarks=remarks,
            db=db
        )
    elif payload.outcome.lower() == "approved":
        # Resolve any open information requests so approved apps do not have dangling open notices
        open_reqs = db.query(InformationRequest).filter(
            InformationRequest.application_id == app.id,
            InformationRequest.status.in_(["action_required", "further_info_required", "submitted", "under_review"])
        ).all()
        for o_req in open_reqs:
            o_req.status = "resolved"
            o_req.updated_at = datetime.now(timezone.utc)

    # Append-only audit trail
    record_audit_event(
        db=db,
        action="RECORD_OFFICIAL_DECISION",
        entity_type="application",
        entity_id=app.id,
        actor=current_user,
        before_state={"status": old_status},
        after_state={"status": app.status, "remarks": remarks, "official": current_user.email}
    )

    # Database-backed notification to institution
    notify_institution(
        db=db,
        institution_id=app.institution_id,
        title=f"Official Determination Recorded: {payload.outcome.upper()}",
        message=f"Scrutiny Committee recorded decision '{payload.outcome.upper()}' on application {app.application_no}. Remarks: {remarks[:120]}...",
        category="decision_recorded",
        application_id=app.id,
        link=f"/applications/{app.id}"
    )

    db.commit()
    db.refresh(decision)

    # Populate extra response fields
    decision.official_name = current_user.full_name or "AICTE Scrutiny Officer"
    decision.reference_no = f"DEC/{app.academic_year}/{app.application_no}"
    decision.issuing_authority = "AICTE Regional Scrutiny Cell"

    return decision

@router.get("/applications/{application_id}/decision", response_model=Optional[DecisionOut])
def get_application_decision(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    decision = db.query(Decision).filter(Decision.application_id == application_id).first()
    if decision:
        decision.official_name = decision.official.full_name if decision.official else "AICTE Scrutiny Officer"
        decision.reference_no = f"DEC/{app.academic_year}/{app.application_no}"
        decision.issuing_authority = "AICTE Regional Scrutiny Cell"

    return decision
