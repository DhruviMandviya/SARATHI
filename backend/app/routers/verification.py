from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user, verify_institution_access, require_official
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.finding import Flag
from backend.app.models.verification import VerificationResult
from backend.app.schemas.verification import VerificationResultOut
from backend.app.engines.verifiers import verify_document, get_verifier_for_doc_type
from backend.app.services.audit import record_audit_event

router = APIRouter(tags=["Authenticity Verification"])

class ManualVerifyRequest(BaseModel):
    reference_no: Optional[str] = None

@router.get("/applications/{application_id}/verification", response_model=List[VerificationResultOut])
def get_application_verification_results(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    # Check existing verification results for documents in this application
    docs = db.query(Document).filter(
        Document.application_id == application_id,
        Document.superseded_by.is_(None)
    ).all()

    doc_ids = [d.id for d in docs]
    existing_all = db.query(VerificationResult).filter(
        VerificationResult.document_id.in_(doc_ids)
    ).order_by(VerificationResult.checked_at.desc()).all() if doc_ids else []

    # Map latest result by document_id
    latest_by_doc: dict[int, VerificationResult] = {}
    for r in existing_all:
        if r.document_id not in latest_by_doc:
            latest_by_doc[r.document_id] = r

    # If any document is missing a verification result, generate it
    new_results_added = False
    for doc in docs:
        if doc.id not in latest_by_doc:
            extracted = doc.extracted_data or {}
            ref_no = (
                extracted.get("reference_no") or
                extracted.get("sanction_no") or
                extracted.get("sanction_number") or
                extracted.get("noc_number") or
                extracted.get("registration_no") or
                extracted.get("deed_number") or
                extracted.get("survey_number") or
                extracted.get("order_no")
            )

            outcome = verify_document(
                doc_type=doc.doc_type,
                reference_no=ref_no,
                document_context=extracted
            )

            v_res = VerificationResult(
                document_id=doc.id,
                authority=outcome.authority,
                adapter_name=outcome.adapter_name,
                reference_no=outcome.reference_no,
                status=outcome.status,
                is_simulated=True,
                raw_response=outcome.raw_response,
                message=outcome.message
            )
            db.add(v_res)
            latest_by_doc[doc.id] = v_res
            new_results_added = True

    if new_results_added:
        db.commit()
        for r in latest_by_doc.values():
            db.refresh(r)

    # Return exactly one result per document
    results = list(latest_by_doc.values())
    if current_user.role == "institution":
        for r in results:
            r.raw_response = {"status": r.status, "redacted": True}
    return results

from backend.app.schemas.verification import VerificationResultOut, RecordManualVerificationRequest
from datetime import datetime, timezone

@router.post("/applications/{application_id}/documents/{document_id}/verify", response_model=VerificationResultOut)
def run_document_verification(
    application_id: int,
    document_id: int,
    req: Optional[ManualVerifyRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.application_id == application_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this application")

    extracted = doc.extracted_data or {}
    ocr_ref = (
        extracted.get("reference_no") or
        extracted.get("sanction_no") or
        extracted.get("sanction_number") or
        extracted.get("noc_number") or
        extracted.get("registration_no") or
        extracted.get("deed_number") or
        extracted.get("survey_number") or
        extracted.get("order_no")
    )
    manual_ref = req.reference_no.strip() if (req and req.reference_no and req.reference_no.strip()) else None
    effective_ref = manual_ref or ocr_ref

    outcome = verify_document(
        doc_type=doc.doc_type,
        reference_no=effective_ref,
        document_context=extracted
    )

    now = datetime.now(timezone.utc)

    # Check if a verification result already exists for this document
    existing = db.query(VerificationResult).filter(VerificationResult.document_id == doc.id).first()
    if existing:
        existing.authority = outcome.authority
        existing.adapter_name = outcome.adapter_name
        existing.reference_no = outcome.reference_no
        existing.status = outcome.status
        existing.is_simulated = True
        existing.verification_mode = "SIMULATED"
        existing.raw_response = outcome.raw_response
        existing.message = outcome.message
        existing.checked_at = now
        if manual_ref:
            existing.manual_reference_no = manual_ref
        if ocr_ref:
            existing.ocr_reference_no = ocr_ref
        v_res = existing
    else:
        v_res = VerificationResult(
            document_id=doc.id,
            authority=outcome.authority,
            adapter_name=outcome.adapter_name,
            reference_no=outcome.reference_no,
            status=outcome.status,
            is_simulated=True,
            verification_mode="SIMULATED",
            manual_reference_no=manual_ref,
            ocr_reference_no=ocr_ref,
            raw_response=outcome.raw_response,
            message=outcome.message,
            checked_at=now
        )
        db.add(v_res)

    # Synchronize internal findings: record mismatch flag or resolve
    if outcome.status == "not_verified":
        mismatch_flag = db.query(Flag).filter(
            Flag.application_id == app.id,
            Flag.document_id == doc.id,
            Flag.category == "verification"
        ).first()
        if not mismatch_flag:
            db.add(Flag(
                application_id=app.id,
                document_id=doc.id,
                category="verification",
                severity="critical",
                title=f"Authority Record Mismatch: {doc.doc_type.replace('_', ' ').title()}",
                explanation=outcome.message or "Issuing authority registry check returned a record mismatch or dispute.",
                evidence={"document_id": doc.id, "authority": outcome.authority, "reference_no": effective_ref, "mode": "SIMULATED"},
                confidence=1.0,
                confidence_meaning="External authority registry response",
                actionability="INTERNAL_REVIEW_ONLY",
                status="open"
            ))
        else:
            mismatch_flag.explanation = outcome.message or "Issuing authority registry check returned a record mismatch or dispute."
            mismatch_flag.status = "open"
    elif outcome.status == "verified":
        mismatch_flag = db.query(Flag).filter(
            Flag.application_id == app.id,
            Flag.document_id == doc.id,
            Flag.category == "verification"
        ).first()
        if mismatch_flag:
            mismatch_flag.status = "acknowledged"

    record_audit_event(
        db=db,
        action="VERIFY_DOCUMENT_SIMULATED",
        entity_type="document",
        entity_id=doc.id,
        actor=current_user,
        after_state={
            "application_id": app.id,
            "document_id": doc.id,
            "status": outcome.status,
            "reference_no": outcome.reference_no,
            "is_simulated": True,
            "verification_mode": "SIMULATED"
        }
    )

    db.commit()
    db.refresh(v_res)
    v_res.checked_reference = v_res.manual_reference_no or v_res.reference_no
    return v_res

@router.post("/applications/{application_id}/documents/{document_id}/manual-verify", response_model=VerificationResultOut)
def record_manual_verification(
    application_id: int,
    document_id: int,
    payload: RecordManualVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Authorised Scrutiny Officer records a controlled manual verification outcome
    (e.g. for self-attested affidavits, physical land deed registers, or offline NOC files).
    Requires substantive officer remarks. Appends immutable audit event.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    verify_institution_access(current_user, app.institution_id)

    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.application_id == application_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this application")

    outcome_map = {
        "verified": "verified",
        "match_confirmed": "verified",
        "not_verified": "not_verified",
        "mismatch_found": "not_verified",
        "mismatch_confirmed": "not_verified",
        "unable_to_verify": "unable_to_verify"
    }
    outcome_key = payload.outcome.lower().strip()
    if outcome_key not in outcome_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid manual verification outcome '{payload.outcome}'. Must be one of: {list(outcome_map.keys())}"
        )

    outcome_status = outcome_map[outcome_key]

    remarks = payload.remarks.strip()
    if len(remarks) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Officer remarks must contain at least 5 characters of substantive rationale."
        )

    now = datetime.now(timezone.utc)
    authority_name = f"Official Scrutiny Committee ({doc.doc_type.replace('_', ' ').title()})"

    if outcome_status == "verified":
        msg = f"Match Confirmed by {current_user.full_name or current_user.email}. Remarks: {remarks}"
    elif outcome_status == "not_verified":
        msg = f"Mismatch Confirmed by {current_user.full_name or current_user.email}. Remarks: {remarks}"
    else:
        msg = f"Unable to Verify by {current_user.full_name or current_user.email}. Remarks: {remarks}"

    ref_to_use = payload.manual_reference_no or (doc.extracted_data or {}).get("reference_no") or None

    existing = db.query(VerificationResult).filter(VerificationResult.document_id == doc.id).first()
    if existing:
        existing.authority = authority_name
        existing.adapter_name = "manual_officer_scrutiny"
        existing.reference_no = ref_to_use
        existing.status = outcome_status
        existing.is_simulated = False
        existing.verification_mode = "MANUAL_SCRUTINY"
        existing.manual_remarks = remarks
        existing.manual_verified_by = current_user.id
        if payload.manual_reference_no:
            existing.manual_reference_no = payload.manual_reference_no
        existing.message = msg
        existing.raw_response = {
            "mode": "manual",
            "evidence_reviewed": payload.evidence_reviewed or "Physical / Digital Certified Scrutiny",
            "officer_email": current_user.email,
            "officer_name": current_user.full_name
        }
        existing.checked_at = now
        v_res = existing
    else:
        v_res = VerificationResult(
            document_id=doc.id,
            authority=authority_name,
            adapter_name="manual_officer_scrutiny",
            reference_no=ref_to_use,
            status=outcome_status,
            is_simulated=False,
            verification_mode="MANUAL_SCRUTINY",
            manual_remarks=remarks,
            manual_verified_by=current_user.id,
            manual_reference_no=payload.manual_reference_no,
            raw_response={
                "mode": "manual",
                "evidence_reviewed": payload.evidence_reviewed or "Physical / Digital Certified Scrutiny",
                "officer_email": current_user.email,
                "officer_name": current_user.full_name
            },
            message=msg,
            checked_at=now
        )
        db.add(v_res)

    # Synchronize internal findings: record mismatch flag or resolve
    if outcome_status == "not_verified":
        mismatch_flag = db.query(Flag).filter(
            Flag.application_id == app.id,
            Flag.document_id == doc.id,
            Flag.category == "verification"
        ).first()
        if not mismatch_flag:
            db.add(Flag(
                application_id=app.id,
                document_id=doc.id,
                category="verification",
                severity="critical",
                title=f"Manual Scrutiny Mismatch: {doc.doc_type.replace('_', ' ').title()}",
                explanation=f"Official manual verification recorded record mismatch/dispute: {remarks}",
                evidence={
                    "document_id": doc.id,
                    "evidence_reviewed": payload.evidence_reviewed or "Physical / Digital Certified Scrutiny",
                    "mode": "MANUAL_SCRUTINY",
                    "reference_no": ref_to_use
                },
                confidence=1.0,
                confidence_meaning="Official manual scrutiny officer determination",
                actionability="INTERNAL_REVIEW_ONLY",
                status="open"
            ))
        else:
            mismatch_flag.explanation = f"Official manual verification recorded record mismatch/dispute: {remarks}"
            mismatch_flag.status = "open"
    elif outcome_status == "verified":
        mismatch_flag = db.query(Flag).filter(
            Flag.application_id == app.id,
            Flag.document_id == doc.id,
            Flag.category == "verification"
        ).first()
        if mismatch_flag:
            mismatch_flag.status = "acknowledged"

    record_audit_event(
        db=db,
        action="RECORD_MANUAL_VERIFICATION",
        entity_type="document",
        entity_id=doc.id,
        actor=current_user,
        after_state={
            "application_id": app.id,
            "document_id": doc.id,
            "outcome": outcome_status,
            "remarks": remarks,
            "evidence_reviewed": payload.evidence_reviewed,
            "verification_mode": "MANUAL_SCRUTINY",
            "reference_no": ref_to_use
        }
    )

    db.commit()
    db.refresh(v_res)
    v_res.checked_reference = v_res.manual_reference_no or v_res.reference_no
    return v_res

