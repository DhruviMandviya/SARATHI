import uuid
from typing import List, Optional, Dict, Any, Tuple
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
from backend.app.services.notification import notify_officials

router = APIRouter(prefix="/applications", tags=["Applications"])

def validate_declared_details_dict(details: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """
    Mandatory field validation for Institution Declared Details.
    Every field is mandatory unless explicitly classified as optional.
    """
    errors: Dict[str, str] = {}
    
    # 1. Institution Name (Mandatory)
    name = (details.get("institution_name") or "").strip() if isinstance(details.get("institution_name"), str) else ""
    if not name:
        errors["institution_name"] = "Institution Legal Name is mandatory."
    elif len(name) < 3:
        errors["institution_name"] = "Institution Name must be at least 3 characters."

    # 2. Trust Name (Mandatory)
    trust = (details.get("trust_name") or "").strip() if isinstance(details.get("trust_name"), str) else ""
    if not trust:
        errors["trust_name"] = "Promoting Trust / Society Name is mandatory."
    elif len(trust) < 3:
        errors["trust_name"] = "Trust Name must be at least 3 characters."

    # 3. Address (Mandatory)
    addr = (details.get("address") or "").strip() if isinstance(details.get("address"), str) else ""
    if not addr:
        errors["address"] = "Campus Address is mandatory."
    elif len(addr) < 5:
        errors["address"] = "Campus Address must be at least 5 characters."

    # 4. State (Mandatory)
    st = (details.get("state") or "").strip() if isinstance(details.get("state"), str) else ""
    if not st:
        errors["state"] = "State / UT is mandatory."

    # 5. Land Area (Acres) (Mandatory, positive float)
    land = details.get("land_area_acres")
    if land is None or land == "":
        errors["land_area_acres"] = "Campus Land Area (in Acres) is mandatory."
    else:
        try:
            val = float(land)
            if val <= 0:
                errors["land_area_acres"] = "Land Area must be greater than 0 acres."
        except (ValueError, TypeError):
            errors["land_area_acres"] = "Land Area must be a valid numeric value."

    # 6. Built-up Area (sqm) (Mandatory, positive float)
    bua = details.get("built_up_area_sqm")
    if bua is None or bua == "":
        errors["built_up_area_sqm"] = "Total Built-up Area (in Sq. Meters) is mandatory."
    else:
        try:
            val = float(bua)
            if val <= 0:
                errors["built_up_area_sqm"] = "Built-up Area must be greater than 0 sq.m."
        except (ValueError, TypeError):
            errors["built_up_area_sqm"] = "Built-up Area must be a valid numeric value."

    # 7. Student Intake (Mandatory, positive integer >= 1)
    intake = details.get("student_intake")
    if intake is None or intake == "":
        errors["student_intake"] = "Total Approved Student Intake is mandatory."
    else:
        try:
            val = int(intake)
            if val < 1:
                errors["student_intake"] = "Student Intake must be at least 1."
        except (ValueError, TypeError):
            errors["student_intake"] = "Student Intake must be an integer."

    # 8. Faculty Count (Mandatory, positive integer >= 1)
    fac = details.get("faculty_count")
    if fac is None or fac == "":
        errors["faculty_count"] = "Total Regular Faculty Count is mandatory."
    else:
        try:
            val = int(fac)
            if val < 1:
                errors["faculty_count"] = "Faculty Count must be at least 1."
        except (ValueError, TypeError):
            errors["faculty_count"] = "Faculty Count must be an integer."

    # 9. Labs Count (Mandatory, integer >= 0)
    labs = details.get("labs_count")
    if labs is None or labs == "":
        errors["labs_count"] = "Core Laboratories Count is mandatory."
    else:
        try:
            val = int(labs)
            if val < 0:
                errors["labs_count"] = "Laboratories Count cannot be negative."
        except (ValueError, TypeError):
            errors["labs_count"] = "Laboratories Count must be an integer."

    # 10. EWS Quota (%) (Mandatory, float >= 0 and <= 100)
    ews = details.get("ews_quota_percentage")
    if ews is None or ews == "":
        errors["ews_quota_percentage"] = "EWS Supernumerary Quota (%) is mandatory."
    else:
        try:
            val = float(ews)
            if val < 0 or val > 100:
                errors["ews_quota_percentage"] = "EWS Quota must be between 0% and 100%."
        except (ValueError, TypeError):
            errors["ews_quota_percentage"] = "EWS Quota must be a valid percentage."

    # 11. Corpus Fund (Lakhs) (Mandatory, float >= 0)
    corpus = details.get("corpus_fund_lakhs")
    if corpus is None or corpus == "":
        errors["corpus_fund_lakhs"] = "Joint Fixed Deposit Reserve (Lakhs) is mandatory."
    else:
        try:
            val = float(corpus)
            if val < 0:
                errors["corpus_fund_lakhs"] = "Corpus Fund cannot be negative."
        except (ValueError, TypeError):
            errors["corpus_fund_lakhs"] = "Corpus Fund must be a valid number."

    # 12. Affidavit Stamp Value (INR) (Mandatory, float >= 10)
    stamp = details.get("affidavit_stamp_value_inr")
    if stamp is None or stamp == "":
        errors["affidavit_stamp_value_inr"] = "Affidavit Stamp Value (INR) is mandatory."
    else:
        try:
            val = float(stamp)
            if val < 10:
                errors["affidavit_stamp_value_inr"] = "Affidavit Stamp Value must be at least ₹10."
        except (ValueError, TypeError):
            errors["affidavit_stamp_value_inr"] = "Affidavit Stamp Value must be a valid number."

    return len(errors) == 0, errors

@router.post("/validate-declared-details")
def validate_declared_details_endpoint(
    details: DeclaredDetails,
    current_user: User = Depends(get_current_user)
):
    """
    Validates declared particulars for frontend pre-checks.
    """
    d_dict = details.model_dump(exclude_unset=True)
    is_valid, errors = validate_declared_details_dict(d_dict)
    return {"is_valid": is_valid, "valid": is_valid, "errors": errors}

@router.post("", response_model=ApplicationOut)
def create_application(
    payload: ApplicationCreate,
    validate_all: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "institution" and not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to an accredited institution."
        )

    target_institution_id = current_user.institution_id if current_user.role == "institution" else 1
    
    declared_dict = payload.declared_details.model_dump(exclude_unset=True) if payload.declared_details else {}

    # Strict validation if validate_all flag is set
    if validate_all:
        is_valid, errors = validate_declared_details_dict(declared_dict)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Institution Declared Details validation failed.", "errors": errors}
            )

    # Generate unique application number
    app_no = f"AICTE-2026-{uuid.uuid4().hex[:6].upper()}"

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
        if status_filter and isinstance(status_filter, str):
            query = query.filter(Application.status == status_filter)
        if search and isinstance(search, str):
            query = query.filter(Application.application_no.ilike(f"%{search}%"))
            
        apps = query.order_by(desc(Application.created_at)).all()
        # Tenant isolation & Redaction: Applicants cannot retrieve internal risk scores
        results = []
        for app in apps:
            app_out = ApplicationOut.model_validate(app)
            app_out.risk_score = 0.0
            app_out.risk_band = ""
            app_out.risk_breakdown = {}
            results.append(app_out)
        return results
    else:
        # Officials/Admins/Auditors can filter by status, state, risk, search
        if status_filter and isinstance(status_filter, str):
            query = query.filter(Application.status == status_filter)
        else:
            # Official active scrutiny queue excludes drafts unless explicitly filtered
            query = query.filter(Application.status != "draft")
        if state_filter and isinstance(state_filter, str):
            query = query.filter(Institution.state.ilike(f"%{state_filter}%"))
        if risk_filter and isinstance(risk_filter, str):
            query = query.filter(Application.risk_band == risk_filter)
        if search and isinstance(search, str):
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

    app_out = ApplicationOut.model_validate(application)
    # Tenant isolation & Redaction: Applicants cannot view internal risk scores or fraud flags
    if current_user.role == "institution":
        app_out.risk_score = 0.0
        app_out.risk_band = ""
        app_out.risk_breakdown = {}

    return app_out

@router.put("/{application_id}/declared-details", response_model=ApplicationOut)
def update_declared_details(
    application_id: int,
    details: DeclaredDetails,
    validate_all: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    # Prevent officials from modifying applicant declared parameters
    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officials cannot modify applicant-submitted declared parameters."
        )

    if application.status not in ("draft", "info_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Declared details cannot be modified when application status is '{application.status}'. Modifications are only permitted in 'draft' or 'info_requested' status."
        )

    # Validate updated values
    raw_dict = details.model_dump(exclude_unset=True)
    if "land_area_acres" in raw_dict and raw_dict["land_area_acres"] is not None:
        if raw_dict["land_area_acres"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Land area must be greater than 0 acres.")
    if "built_up_area_sqm" in raw_dict and raw_dict["built_up_area_sqm"] is not None:
        if raw_dict["built_up_area_sqm"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Built-up area must be greater than 0 sq.m.")
    if "faculty_count" in raw_dict and raw_dict["faculty_count"] is not None:
        if raw_dict["faculty_count"] < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty count must be at least 1.")
    if "student_intake" in raw_dict and raw_dict["student_intake"] is not None:
        if raw_dict["student_intake"] < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student intake must be at least 1.")
    if "ews_quota_percentage" in raw_dict and raw_dict["ews_quota_percentage"] is not None:
        if raw_dict["ews_quota_percentage"] < 0 or raw_dict["ews_quota_percentage"] > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EWS quota must be between 0% and 100%.")

    before_state = dict(application.declared_details or {})
    merged_details = {**before_state, **raw_dict}

    if validate_all:
        is_valid, errs = validate_declared_details_dict(merged_details)
        if not is_valid:
            first_err = next(iter(errs.values()))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=first_err)

    application.declared_details = merged_details

    record_audit_event(
        db=db,
        action="DECLARED_DETAILS_UPDATED",
        entity_type="application",
        entity_id=application.id,
        actor=current_user,
        before_state=before_state,
        after_state=merged_details
    )

    db.commit()
    db.refresh(application)

    app_out = ApplicationOut.model_validate(application)
    if current_user.role == "institution":
        app_out.risk_score = 0.0
        app_out.risk_band = ""
        app_out.risk_breakdown = {}

    return app_out

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
            "processing_stage": doc.processing_stage if doc else None,
            "uploaded_at": doc.uploaded_at.isoformat() if doc and doc.uploaded_at else None,
            "size": doc.size if doc else None,
            "page_count": doc.page_count if doc else None
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
            "processing_error": doc.processing_error,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "size": doc.size
        })

    is_processing = any(d.processing_status in ("queued", "processing") for d in docs)

    # Redact internal risk scores for applicants
    risk_score = 0.0 if current_user.role == "institution" else application.risk_score
    risk_band = "" if current_user.role == "institution" else application.risk_band

    return {
        "application_id": application.id,
        "application_no": application.application_no,
        "status": application.status,
        "is_processing": is_processing,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "documents": doc_statuses
    }

@router.post("/{application_id}/submit")
def submit_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only applicant institution can submit
    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officials cannot submit applications on behalf of institutions."
        )

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    # 1. Validate mandatory checklist items
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

    # 2. Validate mandatory declared parameters
    is_valid_declared, dec_errors = validate_declared_details_dict(application.declared_details or {})
    if not is_valid_declared:
        error_msgs = list(dec_errors.values())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit application: Declared details incomplete or invalid: {'; '.join(error_msgs[:3])}"
        )

    application.status = "submitted"
    application.submitted_at = datetime.now(timezone.utc)

    # Notify officials
    inst_name = application.institution.name if application.institution else "Applicant Institution"
    notify_officials(
        db=db,
        title=f"New Application Submitted: {application.application_no}",
        message=f"{inst_name} has formally submitted application {application.application_no} for AICTE scrutiny review.",
        category="response_submitted",
        application_id=application.id,
        link=f"/applications/{application.id}"
    )

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
