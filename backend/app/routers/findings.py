from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, require_official, verify_institution_access
from backend.app.models.user import User
from backend.app.models.application import Application, ChecklistItem
from backend.app.models.document import Document, ExtractedField
from backend.app.models.finding import Flag
from backend.app.schemas.finding import FlagOut, FlagAcknowledge
from backend.app.engines.validator import validate_application_documents
from backend.app.engines.consistency import check_consistency
from backend.app.services.audit import record_audit_event

router = APIRouter(tags=["Findings & Validation"])

def sync_validation_and_consistency(application_id: int, db: Session):
    """
    Runs validator and consistency engines, creates/updates flags,
    and updates document validation statuses.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        return

    checklist_items = db.query(ChecklistItem).filter(
        ChecklistItem.application_type == app.type
    ).all()
    chk_dicts = [
        {"doc_type": c.doc_type, "mandatory": bool(c.mandatory), "validity_required": bool(c.validity_required), "description": c.description}
        for c in checklist_items
    ]

    docs = db.query(Document).filter(
        Document.application_id == app.id,
        Document.superseded_by.is_(None)
    ).all()
    doc_dicts = [
        {
            "id": d.id,
            "doc_type": d.doc_type,
            "page_count": d.page_count,
            "superseded_by": d.superseded_by,
            "processing_status": d.processing_status,
            "processing_error": d.processing_error
        }
        for d in docs
    ]

    # Map extracted fields by doc_id and by doc_type
    extracted_by_doc_id = {}
    extracted_by_type = {}
    for d in docs:
        fields = db.query(ExtractedField).filter(ExtractedField.document_id == d.id).all()
        f_dict = {f.key: (f.edited_value if f.edited_value is not None else f.value or "") for f in fields}
        extracted_by_doc_id[d.id] = f_dict
        extracted_by_type[d.doc_type] = f_dict

    # 1. Run Document Validator
    val_results = validate_application_documents(
        checklist_items=chk_dicts,
        documents=doc_dicts,
        extracted_fields_by_doc=extracted_by_doc_id
    )

    # Update document validation_status in database
    val_map = {vr.document_id: vr.status for vr in val_results if vr.document_id}
    for d in docs:
        if d.id in val_map:
            d.validation_status = val_map[d.id]
    db.commit()

    # Collect flags from validator
    all_new_flags = []
    for vr in val_results:
        for f in vr.flags:
            f["document_id"] = vr.document_id
            all_new_flags.append(f)

    # 2. Run Consistency Engine
    cons_flags = check_consistency(
        declared_details=app.declared_details or {},
        documents_fields=extracted_by_type
    )
    all_new_flags.extend(cons_flags)

    # 3. Clean up previously generated validation/consistency flags for this application
    db.query(Flag).filter(
        Flag.application_id == app.id,
        Flag.category.in_(["missing", "incomplete", "expired", "mismatch"])
    ).delete()

    # 4. Save new flags to database
    for f in all_new_flags:
        existing = db.query(Flag).filter(
            Flag.application_id == app.id,
            Flag.category == f["category"],
            Flag.title == f["title"]
        ).first()

        if not existing:
            new_flag = Flag(
                application_id=app.id,
                document_id=f.get("document_id"),
                category=f["category"],
                severity=f["severity"],
                title=f["title"],
                explanation=f["explanation"],
                evidence=f["evidence"],
                confidence=f.get("confidence", 1.0),
                confidence_meaning=f.get("confidence_meaning", "Algorithmic rule evaluation"),
                rule_ref=f.get("rule_ref"),
                status="open"
            )
            db.add(new_flag)
    db.commit()

@router.get("/applications/{application_id}/validation")
def get_validation_results(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    # Run check
    sync_validation_and_consistency(application_id, db)

    docs = db.query(Document).filter(
        Document.application_id == app.id,
        Document.superseded_by.is_(None)
    ).all()

    checklist_items = db.query(ChecklistItem).filter(
        ChecklistItem.application_type == app.type
    ).all()

    docs_by_type = {d.doc_type: d for d in docs}
    results = []

    for item in checklist_items:
        doc = docs_by_type.get(item.doc_type)
        results.append({
            "doc_type": item.doc_type,
            "description": item.description,
            "mandatory": bool(item.mandatory),
            "is_uploaded": doc is not None,
            "document_id": doc.id if doc else None,
            "original_filename": doc.original_filename if doc else None,
            "validation_status": doc.validation_status if doc else ("missing" if item.mandatory else "not_uploaded"),
            "processing_status": doc.processing_status if doc else None,
            "official_verification_status": getattr(doc, "official_verification_status", None) if doc else None,
            "official_verification_remarks": getattr(doc, "official_verification_remarks", None) if doc else None,
            "official_verified_by": getattr(doc, "official_verified_by", None) if doc else None,
            "official_verified_at": doc.official_verified_at.isoformat() if (doc and getattr(doc, "official_verified_at", None)) else None,
        })

    return {
        "application_id": app.id,
        "items": results
    }

@router.get("/applications/{application_id}/findings", response_model=List[FlagOut])
def get_application_findings(
    application_id: int,
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    query = db.query(Flag).filter(Flag.application_id == application_id)

    # If institution, filter out forensic-level signals (tampering/forensic details) per architecture
    if current_user.role == "institution":
        query = query.filter(Flag.category.in_(["missing", "expired", "incomplete", "mismatch", "quality"]))

    if category:
        query = query.filter(Flag.category == category)
    if severity:
        query = query.filter(Flag.severity == severity)
    if status_filter:
        query = query.filter(Flag.status == status_filter)

    return query.order_by(Flag.created_at.desc()).all()

@router.post("/findings/{flag_id}/acknowledge", response_model=FlagOut)
def acknowledge_flag(
    flag_id: int,
    payload: FlagAcknowledge,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    flag = db.query(Flag).filter(Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    before_state = {"status": flag.status, "reason": flag.dismissed_reason}
    flag.status = payload.status
    if payload.status == "dismissed":
        flag.dismissed_reason = payload.reason or "Dismissed by official reviewer"
        flag.dismissed_by = current_user.id
    elif payload.status == "acknowledged":
        flag.dismissed_reason = payload.reason or "Acknowledged for review"

    record_audit_event(
        db=db,
        action=f"flag_{payload.status}",
        entity_type="flag",
        entity_id=flag.id,
        actor=current_user,
        before_state=before_state,
        after_state={"status": flag.status, "reason": flag.dismissed_reason}
    )

    db.commit()
    db.refresh(flag)
    return flag
