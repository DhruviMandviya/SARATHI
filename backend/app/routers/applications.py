import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, verify_institution_access
from backend.app.models.user import User
from backend.app.models.institution import Institution
from backend.app.models.application import Application, ChecklistItem
from backend.app.models.document import Document
from backend.app.schemas.application import ApplicationCreate, ApplicationOut, DeclaredDetails, ChecklistItemOut
from backend.app.services.audit import record_audit_event

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationOut)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "institution" and not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to an accredited institution."
        )

    target_institution_id = current_user.institution_id if current_user.role == "institution" else 1
    
    # Generate unique application number
    app_no = f"AICTE-2026-{uuid.uuid4().hex[:6].upper()}"

    declared_dict = payload.declared_details.model_dump() if payload.declared_details else {}

    application = Application(
        application_no=app_no,
        institution_id=target_institution_id,
        type=payload.type,
        academic_year=payload.academic_year,
        status="draft",
        risk_score=0.0,
        risk_band="Low",
        risk_breakdown={},
        declared_details=declared_dict,
        created_at=datetime.now(timezone.utc)
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    record_audit_event(
        db=db,
        action="application_created",
        entity_type="application",
        entity_id=application.id,
        actor=current_user,
        after_state={"application_no": application.application_no, "status": "draft"}
    )

    return application

@router.get("", response_model=List[ApplicationOut])
def list_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    state_filter: Optional[str] = Query(None, alias="state"),
    risk_filter: Optional[str] = Query(None, alias="risk"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Application).join(Institution, Application.institution_id == Institution.id)

    # Role-based restriction: Institutions can ONLY see their own applications
    if current_user.role == "institution":
        query = query.filter(Application.institution_id == current_user.institution_id)
    else:
        # Officials/Admins/Auditors can filter by status, state, risk, search
        if status_filter:
            query = query.filter(Application.status == status_filter)
        if state_filter:
            query = query.filter(Institution.state.ilike(f"%{state_filter}%"))
        if risk_filter:
            query = query.filter(Application.risk_band == risk_filter)
        if search:
            query = query.filter(
                (Application.application_no.ilike(f"%{search}%")) |
                (Institution.name.ilike(f"%{search}%"))
            )

    return query.order_by(desc(Application.created_at)).all()

@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)
    return application

@router.put("/{application_id}/declared-details", response_model=ApplicationOut)
def update_declared_details(
    application_id: int,
    details: DeclaredDetails,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    before_state = application.declared_details
    new_details = details.model_dump(exclude_unset=True)
    merged_details = {**before_state, **new_details}
    application.declared_details = merged_details

    record_audit_event(
        db=db,
        action="declared_details_updated",
        entity_type="application",
        entity_id=application.id,
        actor=current_user,
        before_state=before_state,
        after_state=merged_details
    )

    db.commit()
    db.refresh(application)
    return application

@router.get("/{application_id}/checklist")
def get_application_checklist(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    checklist_items = db.query(ChecklistItem).filter(
        ChecklistItem.application_type == application.type
    ).all()

    # Get active (non-superseded) documents
    docs = db.query(Document).filter(
        Document.application_id == application.id,
        Document.superseded_by.is_(None)
    ).all()
    docs_by_type = {doc.doc_type: doc for doc in docs}

    results = []
    missing_mandatory = []

    for item in checklist_items:
        doc = docs_by_type.get(item.doc_type)
        is_uploaded = doc is not None
        doc_status = doc.validation_status if doc else ("missing" if item.mandatory else "not_uploaded")

        if item.mandatory and not is_uploaded:
            missing_mandatory.append(item.doc_type)

        results.append({
            "checklist_item_id": item.id,
            "doc_type": item.doc_type,
            "description": item.description,
            "mandatory": bool(item.mandatory),
            "validity_required": bool(item.validity_required),
            "is_uploaded": is_uploaded,
            "document_id": doc.id if doc else None,
            "original_filename": doc.original_filename if doc else None,
            "validation_status": doc_status,
            "processing_status": doc.processing_status if doc else None,
            "processing_stage": doc.processing_stage if doc else None
        })

    return {
        "application_id": application.id,
        "can_submit": len(missing_mandatory) == 0,
        "missing_mandatory": missing_mandatory,
        "items": results
    }

@router.get("/{application_id}/status")
def get_application_status(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    docs = db.query(Document).filter(
        Document.application_id == application.id,
        Document.superseded_by.is_(None)
    ).all()

    doc_statuses = []
    for doc in docs:
        doc_statuses.append({
            "id": doc.id,
            "doc_type": doc.doc_type,
            "original_filename": doc.original_filename,
            "processing_status": doc.processing_status,
            "processing_stage": doc.processing_stage,
            "validation_status": doc.validation_status,
            "page_count": doc.page_count,
            "processing_error": doc.processing_error
        })

    is_processing = any(d.processing_status in ("queued", "processing") for d in docs)

    return {
        "application_id": application.id,
        "application_no": application.application_no,
        "status": application.status,
        "is_processing": is_processing,
        "risk_score": application.risk_score,
        "risk_band": application.risk_band,
        "documents": doc_statuses
    }

@router.post("/{application_id}/submit")
def submit_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    # Check mandatory checklist items
    mandatory_items = db.query(ChecklistItem).filter(
        ChecklistItem.application_type == application.type,
        ChecklistItem.mandatory == 1
    ).all()

    uploaded_docs = db.query(Document).filter(
        Document.application_id == application.id,
        Document.superseded_by.is_(None)
    ).all()
    uploaded_types = {d.doc_type for d in uploaded_docs}

    missing = [m.doc_type for m in mandatory_items if m.doc_type not in uploaded_types]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit application: Mandatory documents missing: {', '.join(missing)}"
        )

    application.status = "submitted"
    application.submitted_at = datetime.now(timezone.utc)

    record_audit_event(
        db=db,
        action="application_submitted",
        entity_type="application",
        entity_id=application.id,
        actor=current_user,
        after_state={"status": "submitted", "submitted_at": str(application.submitted_at)}
    )

    db.commit()
    db.refresh(application)
    return {"message": "Application submitted successfully", "status": application.status}
