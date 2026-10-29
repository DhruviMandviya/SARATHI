import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, require_official, verify_institution_access
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.institution import Institution
from backend.app.models.document import Document
from backend.app.models.information_request import InformationRequest, InformationResponse
from backend.app.schemas.information_request import (
    InformationRequestOut,
    InformationRequestCreate,
    InformationResponseSave,
    InformationResponseOut,
    InformationRequestDetailOut,
    InformationRequestSummaryCards,
    NoticeCandidatesResponse,
    NoticeBuilderIssueRequest
)
from backend.app.services.notification import notify_institution, notify_officials
from backend.app.services.audit import record_audit_event
from backend.app.services.file_validation import validate_and_save_upload

router = APIRouter(tags=["Information Requests & Notices"])

from backend.app.services.notice_sync import sync_unpersisted_info_requested_notices

@router.get("/information-requests/summary-cards", response_model=InformationRequestSummaryCards)
def get_information_requests_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ensure any applications marked info_requested are synchronized with official notice records
    sync_unpersisted_info_requested_notices(db)

    query = db.query(InformationRequest)
    if current_user.role == "institution":
        # Drafts must NEVER be shown to applicants
        query = query.filter(
            InformationRequest.institution_id == current_user.institution_id,
            InformationRequest.status != "draft"
        )

    action_required = query.filter(InformationRequest.status.in_(["action_required", "further_info_required"])).count()
    response_submitted = query.filter(InformationRequest.status == "submitted").count()
    under_review = query.filter(InformationRequest.status == "under_review").count()
    resolved = query.filter(InformationRequest.status == "resolved").count()
    total = query.count()

    return InformationRequestSummaryCards(
        action_required=action_required,
        response_submitted=response_submitted,
        under_review=under_review,
        resolved=resolved,
        total=total
    )

@router.get("/information-requests", response_model=List[InformationRequestOut])
def list_information_requests(
    application_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ensure any applications marked info_requested are synchronized with official notice records
    sync_unpersisted_info_requested_notices(db)

    query = db.query(InformationRequest)

    if current_user.role == "institution":
        if not current_user.institution_id:
            return []
        # Tenant isolation: strictly only notices formally issued to logged-in institution
        # Drafts must NEVER be shown to applicant
        query = query.filter(
            InformationRequest.institution_id == current_user.institution_id,
            InformationRequest.status != "draft"
        )
    
    if application_id:
        query = query.filter(InformationRequest.application_id == application_id)
        
    if status_filter and status_filter.strip() and status_filter.strip() != "all":
        if status_filter == "action_required":
            query = query.filter(InformationRequest.status.in_(["action_required", "further_info_required"]))
        else:
            query = query.filter(InformationRequest.status == status_filter.strip())

    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                InformationRequest.reference_no.ilike(s),
                InformationRequest.title.ilike(s),
                InformationRequest.reason.ilike(s)
            )
        )

    items = query.order_by(desc(InformationRequest.issued_at)).all()
    # Populate related display fields
    for it in items:
        if it.application:
            it.application_no = it.application.application_no
        if it.institution:
            it.institution_name = it.institution.name

    return items

@router.get("/information-requests/{request_id}", response_model=InformationRequestDetailOut)
def get_information_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    if current_user.role == "institution":
        # Tenant isolation
        verify_institution_access(current_user, req.institution_id)
        # Drafts must NEVER be shown as an issued notice to applicant
        if req.status == "draft":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice is in draft and not yet issued")

    app = req.application
    inst = req.institution
    app_no = app.application_no if app else f"APP-{req.application_id}"
    inst_name = inst.name if inst else "Applicant Institution"

    req.application_no = app_no
    req.institution_name = inst_name

    responses = db.query(InformationResponse).filter(
        InformationResponse.request_id == req.id
    ).order_by(desc(InformationResponse.version)).all()

    for r in responses:
        r.receipt_no = r.submission_receipt

    latest_response = responses[0] if responses else None
    
    # Check if a released official notice document or deficiency letter exists
    has_released_doc = bool(req.notice_text and req.status != "draft")

    return InformationRequestDetailOut(
        request=req,
        application_no=app_no,
        institution_name=inst_name,
        latest_response=latest_response,
        response_history=[r for r in responses if r.status == "submitted"],
        has_released_notice_doc=has_released_doc
    )

@router.post("/applications/{application_id}/information-requests", response_model=InformationRequestOut)
def issue_information_request(
    application_id: int,
    payload: InformationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Authorized council official issues a formal Information Request / Deficiency Notice.
    Applicants can NEVER issue a notice.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    ref_no = f"NOT-2026-{uuid.uuid4().hex[:6].upper()}"
    
    # Compute or set deadline
    now = datetime.now(timezone.utc)
    if payload.deadline_date:
        deadline = payload.deadline_date
    else:
        days = payload.deadline_days or 15
        deadline = now + timedelta(days=days)

    deficiencies_json = [d.model_dump() for d in payload.deficiencies]

    req = InformationRequest(
        reference_no=ref_no,
        application_id=app.id,
        institution_id=app.institution_id,
        title=payload.title,
        reason=payload.reason,
        notice_text=payload.notice_text or payload.reason,
        status="action_required",
        issuing_authority="AICTE Scrutiny Committee",
        issued_by=current_user.id,
        issued_at=now,
        deadline=deadline,
        deficiencies=deficiencies_json,
        created_at=now
    )
    db.add(req)

    # Update application status
    old_status = app.status
    app.status = "info_requested"

    # Notify institution
    notify_institution(
        db=db,
        institution_id=app.institution_id,
        title=f"Statutory Notice Issued: {payload.title}",
        message=f"Deficiency Notice {ref_no} issued for application {app.application_no}. Response deadline: {deadline.strftime('%d %b %Y')}.",
        category="notice_issued",
        application_id=app.id,
        link=f"/information-requests/{req.id}",
        reference_id=ref_no
    )

    record_audit_event(
        db=db,
        action="ISSUE_INFORMATION_REQUEST",
        entity_type="information_request",
        entity_id=app.id,
        actor=current_user,
        before_state={"status": old_status},
        after_state={"reference_no": ref_no, "status": "action_required", "deadline": str(deadline)}
    )

    db.commit()
    db.refresh(req)
    return req

@router.post("/information-requests/{request_id}/response/draft", response_model=InformationResponseOut)
def save_response_draft(
    request_id: int,
    payload: InformationResponseSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Applicant saves draft response. Only institution users can save responses.
    """
    if current_user.role != "institution":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only applicant institutions can submit responses")

    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    verify_institution_access(current_user, req.institution_id)

    if req.status in ("resolved",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is already resolved")

    # Find existing draft response or create new draft version
    existing_draft = db.query(InformationResponse).filter(
        InformationResponse.request_id == req.id,
        InformationResponse.status == "draft"
    ).first()

    items_json = [it.model_dump() for it in payload.items]

    if existing_draft:
        existing_draft.items = items_json
        existing_draft.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_draft)
        return existing_draft
    else:
        # Determine next version
        highest_version = db.query(InformationResponse).filter(
            InformationResponse.request_id == req.id
        ).order_by(desc(InformationResponse.version)).first()
        next_ver = (highest_version.version + 1) if highest_version else 1

        new_resp = InformationResponse(
            request_id=req.id,
            application_id=req.application_id,
            institution_id=req.institution_id,
            version=next_ver,
            status="draft",
            items=items_json,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_resp)
        db.commit()
        db.refresh(new_resp)
        return new_resp

@router.post("/information-requests/{request_id}/response/submit", response_model=InformationResponseOut)
def submit_response(
    request_id: int,
    payload: InformationResponseSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Applicant submits formal response. Validates all required responses and attachments.
    Issues receipt and notifies officials.
    """
    if current_user.role != "institution":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only applicant institutions can submit responses")

    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    verify_institution_access(current_user, req.institution_id)

    if req.status == "resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is already resolved")

    # Validate all mandatory deficiencies have explanations and uploaded attachments
    deficiencies = req.deficiencies or []
    items_by_def = {it.deficiency_id: it for it in payload.items}

    incomplete_items = []
    for d in deficiencies:
        def_id = d.get("id")
        resp_item = items_by_def.get(def_id)
        if not resp_item:
            incomplete_items.append(f"{d.get('requirement', def_id)}: Response missing")
        else:
            explanation = (resp_item.explanation or "").strip()
            if not explanation:
                incomplete_items.append(f"{d.get('requirement', def_id)}: Explanation is required")
            if d.get("mandatory", True) and not resp_item.document_id:
                incomplete_items.append(f"{d.get('requirement', def_id)}: Document attachment is required")

    if incomplete_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incomplete submission items: {'; '.join(incomplete_items)}"
        )

    receipt_no = f"RCP-2026-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)

    # Check if there's an existing draft to upgrade, or create fresh
    existing_draft = db.query(InformationResponse).filter(
        InformationResponse.request_id == req.id,
        InformationResponse.status == "draft"
    ).first()

    items_json = [it.model_dump() for it in payload.items]

    if existing_draft:
        existing_draft.items = items_json
        existing_draft.status = "submitted"
        existing_draft.submission_receipt = receipt_no
        existing_draft.submitted_at = now
        existing_draft.submitted_by = current_user.id
        resp = existing_draft
    else:
        highest_version = db.query(InformationResponse).filter(
            InformationResponse.request_id == req.id
        ).order_by(desc(InformationResponse.version)).first()
        next_ver = (highest_version.version + 1) if highest_version else 1

        resp = InformationResponse(
            request_id=req.id,
            application_id=req.application_id,
            institution_id=req.institution_id,
            version=next_ver,
            status="submitted",
            items=items_json,
            submission_receipt=receipt_no,
            submitted_at=now,
            submitted_by=current_user.id,
            created_at=now
        )
        db.add(resp)

    # Transition Request status
    req.status = "submitted"
    req.updated_at = now

    # Transition Application status
    app = req.application
    if app:
        app.status = "needs_review"

    # Notify council scrutiny officials
    notify_officials(
        db=db,
        title=f"Response Submitted: Notice {req.reference_no}",
        message=f"{req.institution.name if req.institution else 'Institution'} submitted formal response for {app.application_no if app else ''}. Receipt: {receipt_no}. Review required.",
        category="response_submitted",
        application_id=req.application_id,
        link=f"/applications/{req.application_id}",
        reference_id=receipt_no
    )

    record_audit_event(
        db=db,
        action="SUBMIT_INFORMATION_RESPONSE",
        entity_type="information_response",
        entity_id=req.id,
        actor=current_user,
        after_state={"receipt": receipt_no, "request_id": req.id, "submitted_at": str(now)}
    )

    db.commit()
    db.refresh(resp)
    resp.receipt_no = resp.submission_receipt
    return resp

@router.get("/information-requests/{request_id}/notice-doc")
def download_notice_document(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    if current_user.role == "institution":
        verify_institution_access(current_user, req.institution_id)
        if req.status == "draft":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice is in draft and not yet issued")

    from fastapi.responses import Response
    text_content = req.notice_text or req.reason
    safe_ref = req.reference_no.replace("/", "_")
    filename = f"Deficiency_Notice_{safe_ref}.txt"
    return Response(
        content=text_content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

class OfficialReviewPayload(BaseModel):
    action: Optional[str] = None
    outcome: Optional[str] = None
    remarks: Optional[str] = None
    notes: Optional[str] = None

@router.post("/information-requests/{request_id}/review")
def review_information_request(
    request_id: int,
    action: Optional[str] = Query(None, description="under_review | further_info_required | resolved"),
    remarks: Optional[str] = Query(None, description="Official remarks"),
    payload: Optional[OfficialReviewPayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Authorized officials review submitted response or resolve request.
    Applicants cannot close requests unilaterally.
    """
    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    eff_action = action or (payload.action if payload else None) or (payload.outcome if payload else None) or "resolved"
    eff_remarks = remarks or (payload.remarks if payload else None) or (payload.notes if payload else None) or ""

    valid_actions = ["under_review", "further_info_required", "resolved"]
    if eff_action not in valid_actions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Action must be one of: {valid_actions}")

    old_status = req.status
    req.status = eff_action
    req.updated_at = datetime.now(timezone.utc)

    # Notify institution on official action
    if eff_action == "further_info_required":
        notify_institution(
            db=db,
            institution_id=req.institution_id,
            title=f"Further Information Required: Notice {req.reference_no}",
            message=f"The Scrutiny Committee has reviewed your response and requested further clarification: {eff_remarks or 'See request details.'}",
            category="further_info_requested",
            application_id=req.application_id,
            link=f"/information-requests/{req.id}",
            reference_id=req.reference_no
        )
    elif eff_action == "resolved":
        notify_institution(
            db=db,
            institution_id=req.institution_id,
            title=f"Notice Resolved: {req.reference_no}",
            message=f"Deficiency Notice {req.reference_no} has been marked resolved by the Scrutiny Committee.",
            category="request_resolved",
            application_id=req.application_id,
            link=f"/information-requests/{req.id}",
            reference_id=req.reference_no
        )
        if req.application:
            req.application.status = "under_verification"

    record_audit_event(
        db=db,
        action="REVIEW_INFORMATION_REQUEST",
        entity_type="information_request",
        entity_id=req.id,
        actor=current_user,
        before_state={"status": old_status},
        after_state={"status": eff_action, "remarks": eff_remarks}
    )

    db.commit()
    return {"message": f"Request status transitioned to '{eff_action}'", "status": req.status}

@router.post("/information-requests/{request_id}/upload-deficiency-doc")
async def upload_deficiency_document(
    request_id: int,
    file: UploadFile = File(...),
    deficiency_id: str = Form(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dedicated document upload for a specific deficiency slot.
    Operates on its own slot and uses standard validate_and_save_upload.
    """
    if current_user.role != "institution":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only applicant institutions can upload deficiency documents")

    req = db.query(InformationRequest).filter(InformationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information request not found")

    verify_institution_access(current_user, req.institution_id)

    val_result = await validate_and_save_upload(file)
    if not val_result.is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=val_result.error_message)

    doc = Document(
        application_id=req.application_id,
        doc_type=doc_type,
        original_filename=val_result.sanitized_filename,
        stored_path=val_result.storage_rel_path,
        mime_type=val_result.mime_type,
        size=val_result.size_bytes if hasattr(val_result, "size_bytes") else 1024,
        sha256=val_result.sha256,
        page_count=val_result.page_count,
        processing_status="completed",
        processing_stage="Uploaded for Cure Notice",
        validation_status="valid"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "original_filename": doc.original_filename,
        "doc_type": doc.doc_type,
        "deficiency_id": deficiency_id,
        "size": doc.size
    }

@router.get("/applications/{application_id}/notice-candidates", response_model=NoticeCandidatesResponse)
def get_notice_candidates(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Returns candidate findings grouped by regulatory category for the Notice Builder.
    Distinguishes applicant-actionable items from internal-only scrutiny signals.
    """
    from backend.app.services.finding_classification import get_candidate_notice_items
    try:
        candidates = get_candidate_notice_items(application_id, db)
        return candidates
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/applications/{application_id}/issue-notice-builder", response_model=InformationRequestOut)
def issue_notice_builder(
    application_id: int,
    payload: NoticeBuilderIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Issues a focused, formal Statutory Deficiency Notice constructed via the Notice Builder.
    Only includes explicitly selected applicant-actionable items.
    Requires substantive official remarks and >= 1 selected item.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if not payload.selected_items or len(payload.selected_items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A deficiency notice must include at least one valid applicant-actionable item."
        )

    remarks = (payload.remarks or payload.official_remarks or "").strip()
    if len(remarks) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official remarks must contain substantive scrutiny directives."
        )

    now = datetime.now(timezone.utc)
    if payload.deadline_date:
        deadline = payload.deadline_date
    else:
        days = payload.cure_period_days or payload.deadline_days or 15
        deadline = now + timedelta(days=days)

    ref_no = f"AICTE/RO/SCRUTINY/{app.academic_year}/{app.application_no}/DEF-01"

    # Convert selected items into persistent deficiency items
    def_items = []
    for idx, it in enumerate(payload.selected_items, start=1):
        def_items.append({
            "id": f"def-{idx}",
            "finding_id": it.finding_id,
            "category": it.category or "mandatory_compliance",
            "doc_type": it.doc_type or "general_compliance",
            "requirement": it.requirement or it.title or f"Deficiency Item #{idx}",
            "explanation": it.explanation,
            "requested_action": it.requested_action,
            "requires_explanation": it.requires_explanation,
            "requires_upload": it.requires_upload,
            "mandatory": it.mandatory,
            "response_status": "pending",
            "official_review_status": "pending",
            "official_remarks": ""
        })

    # Build or use letter text
    if payload.notice_text and payload.notice_text.strip():
        letter_text = payload.notice_text.strip()
    else:
        from backend.app.services.deficiency_letter import generate_deficiency_letter_text
        letter_data = generate_deficiency_letter_text(app.id, db)
        letter_text = letter_data.get("letter_text", remarks)

    # Check existing notice (idempotent update or create new)
    existing_req = db.query(InformationRequest).filter(
        InformationRequest.application_id == app.id
    ).order_by(desc(InformationRequest.id)).first()

    if existing_req:
        existing_req.reference_no = ref_no
        existing_req.title = f"Scrutiny Deficiency Notice regarding Application for Approval ({app.academic_year})"
        existing_req.reason = remarks
        existing_req.notice_text = letter_text
        existing_req.status = "action_required"
        existing_req.deficiencies = def_items
        existing_req.issued_by = current_user.id
        existing_req.issued_at = now
        existing_req.deadline = deadline
        existing_req.updated_at = now
        req = existing_req
    else:
        req = InformationRequest(
            reference_no=ref_no,
            application_id=app.id,
            institution_id=app.institution_id,
            title=f"Scrutiny Deficiency Notice regarding Application for Approval ({app.academic_year})",
            reason=remarks,
            notice_text=letter_text,
            status="action_required",
            issuing_authority="AICTE Scrutiny Committee",
            issued_by=current_user.id,
            issued_at=now,
            deadline=deadline,
            deficiencies=def_items,
            created_at=now
        )
        db.add(req)

    # Update application status to info_requested
    app.status = "info_requested"

    # Update Decision record
    from backend.app.models.decision import Decision, DeficiencyLetter
    dec = db.query(Decision).filter(Decision.application_id == application_id).first()
    if dec:
        dec.outcome = "info_requested"
        dec.remarks = remarks
        dec.official_id = current_user.id
        dec.decided_at = now
    else:
        dec = Decision(
            application_id=app.id,
            official_id=current_user.id,
            outcome="info_requested",
            remarks=remarks,
            decided_at=now
        )
        db.add(dec)

    # Update DeficiencyLetter record
    dl = db.query(DeficiencyLetter).filter(DeficiencyLetter.application_id == app.id).first()
    if dl:
        dl.edited_text = letter_text
        dl.status = "sent"
        dl.updated_at = now
    else:
        dl = DeficiencyLetter(
            application_id=app.id,
            draft_text=letter_text,
            edited_text=letter_text,
            status="sent",
            created_by=current_user.id,
            created_at=now,
            updated_at=now
        )
        db.add(dl)

    record_audit_event(
        db=db,
        action="ISSUE_DEFICIENCY_NOTICE_BUILDER",
        entity_type="information_request",
        entity_id=app.id,
        actor=current_user,
        before_state={"status": app.status},
        after_state={"reference_no": ref_no, "deficiency_count": len(def_items), "deadline": str(deadline)}
    )

    notify_institution(
        db=db,
        institution_id=app.institution_id,
        title=f"Statutory Notice Issued: {ref_no}",
        message=f"Deficiency Notice {ref_no} has been issued with {len(def_items)} actionable item(s). Response deadline: {deadline.strftime('%d %B %Y')}.",
        category="notice_issued",
        application_id=app.id,
        link=f"/information-requests/{req.id if req.id else ''}",
        reference_id=ref_no
    )

    db.commit()
    db.refresh(req)

    req.application_no = app.application_no
    req.institution_name = app.institution.name if app.institution else ""
    return req

