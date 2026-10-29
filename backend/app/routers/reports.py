from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, verify_institution_access, require_official
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.engines.risk import RiskEngine
from backend.app.services.pdf_report import generate_application_pdf_report
from backend.app.services.deficiency_letter import generate_deficiency_letter_text
from backend.app.services.audit import record_audit_event

router = APIRouter(tags=["Reports & Deficiency Letters"])

class DeficiencyLetterUpdateRequest(BaseModel):
    letter_text: str

@router.get("/applications/{application_id}/report")
def get_application_report_summary(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    # For institutions, strictly hide internal risk scores and contributing factor breakdowns
    if current_user.role == "institution":
        return {
            "application_id": app.id,
            "application_no": app.application_no,
            "academic_year": app.academic_year,
            "type": app.type,
            "status": app.status,
            "risk_score": 0.0,
            "risk_band": "",
            "risk_breakdown": {},
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        }

    risk_engine = RiskEngine(db)
    breakdown = risk_engine.calculate_application_risk(application_id)

    return {
        "application_id": app.id,
        "application_no": app.application_no,
        "academic_year": app.academic_year,
        "type": app.type,
        "status": app.status,
        "risk_score": breakdown["score"],
        "risk_band": breakdown["band"],
        "risk_breakdown": breakdown,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
    }

@router.get("/applications/{application_id}/report.pdf")
def download_application_pdf_report(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    pdf_bytes = generate_application_pdf_report(application_id, db)

    # Log PDF download in audit trail
    record_audit_event(
        db=db,
        action="DOWNLOAD_PDF_REPORT",
        entity_type="application",
        entity_id=app.id,
        actor=current_user,
        after_state={"filename": f"AICTE_Dossier_{app.application_no}.pdf"}
    )

    filename = f"AICTE_Scrutiny_Dossier_{app.application_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@router.get("/applications/{application_id}/deficiency-letter")
def get_deficiency_letter(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    from backend.app.models.information_request import InformationRequest
    from backend.app.models.decision import DeficiencyLetter

    # Check for formally issued InformationRequest
    issued_notice = db.query(InformationRequest).filter(
        InformationRequest.application_id == application_id,
        InformationRequest.status != "draft"
    ).order_by(desc(InformationRequest.id)).first()

    if current_user.role == "institution":
        # Applicants only see notices AFTER an authorized official has formally issued it.
        # Drafts must NEVER be exposed as official applicant instructions.
        if not issued_notice:
            raise HTTPException(
                status_code=404,
                detail="No official deficiency notice has been issued yet for this application."
            )
        return {
            "id": issued_notice.id,
            "application_id": app.id,
            "application_no": app.application_no,
            "reference_no": issued_notice.reference_no,
            "generated_date": issued_notice.issued_at.strftime("%d %B %Y"),
            "cure_deadline": issued_notice.deadline.strftime("%d %B %Y"),
            "deficiency_count": len(issued_notice.deficiencies),
            "deficiencies": issued_notice.deficiencies,
            "letter_text": issued_notice.notice_text or issued_notice.reason,
            "status": issued_notice.status,
            "is_issued": True
        }

    # Officials can view existing issued notice, saved draft, or auto-generated draft
    if issued_notice:
        return {
            "id": issued_notice.id,
            "application_id": app.id,
            "application_no": app.application_no,
            "reference_no": issued_notice.reference_no,
            "generated_date": issued_notice.issued_at.strftime("%d %B %Y"),
            "cure_deadline": issued_notice.deadline.strftime("%d %B %Y"),
            "deficiency_count": len(issued_notice.deficiencies),
            "deficiencies": issued_notice.deficiencies,
            "letter_text": issued_notice.notice_text or issued_notice.reason,
            "status": issued_notice.status,
            "is_issued": True
        }

    def_letter = db.query(DeficiencyLetter).filter(
        DeficiencyLetter.application_id == application_id
    ).first()

    if def_letter and def_letter.edited_text:
        letter_data = generate_deficiency_letter_text(application_id, db)
        letter_data["letter_text"] = def_letter.edited_text
        letter_data["status"] = def_letter.status
        letter_data["is_issued"] = False
        return letter_data

    letter_data = generate_deficiency_letter_text(application_id, db)
    letter_data["is_issued"] = False
    return letter_data

@router.post("/applications/{application_id}/deficiency-letter")
def update_deficiency_letter(
    application_id: int,
    payload: DeficiencyLetterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    from backend.app.models.decision import DeficiencyLetter
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    def_letter = db.query(DeficiencyLetter).filter(
        DeficiencyLetter.application_id == application_id
    ).first()

    if def_letter:
        def_letter.edited_text = payload.letter_text
        def_letter.updated_at = now
    else:
        def_letter = DeficiencyLetter(
            application_id=app.id,
            draft_text=payload.letter_text,
            edited_text=payload.letter_text,
            status="draft",
            created_by=current_user.id,
            created_at=now,
            updated_at=now
        )
        db.add(def_letter)

    # Record official edit to deficiency letter
    record_audit_event(
        db=db,
        action="UPDATE_DEFICIENCY_LETTER",
        entity_type="application",
        entity_id=app.id,
        actor=current_user,
        after_state={"letter_text": payload.letter_text[:500], "status": "draft"}
    )

    db.commit()

    return {
        "status": "success",
        "message": "Deficiency letter draft saved and recorded in audit log.",
        "letter_text": payload.letter_text
    }
