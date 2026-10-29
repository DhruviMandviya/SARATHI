import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import imagehash
from PIL import Image
import fitz

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.permissions import get_current_user, require_official, verify_institution_access
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.document import Document, ExtractedField
from backend.app.schemas.document import DocumentOut, ExtractedFieldOut, FieldUpdate, OfficialDocumentReviewRequest
from backend.app.services.file_validation import validate_and_save_upload
from backend.app.services.audit import record_audit_event
from backend.app.pipeline.orchestrator import process_document_pipeline

router = APIRouter(tags=["Documents"])

def compute_phash_for_file(stored_path: str, mime_type: str) -> Optional[str]:
    """Computes perceptual hash (pHash) on the first page of PDF or image."""
    try:
        if "pdf" in mime_type:
            doc = fitz.open(stored_path)
            if len(doc) > 0:
                pix = doc[0].get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                h = imagehash.phash(img)
                doc.close()
                return str(h)
            doc.close()
        else:
            with Image.open(stored_path) as img:
                h = imagehash.phash(img.convert("RGB"))
                return str(h)
    except Exception:
        pass
    return None

@router.post("/applications/{application_id}/documents", response_model=DocumentOut)
async def upload_document(
    application_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    verify_institution_access(current_user, application.institution_id)

    # Prevent officials from modifying applicant-submitted documents through Applications Queue
    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officials cannot upload or replace applicant-submitted documents through the applications queue."
        )

    # Restrict uploads for institutions to editable states
    if application.status not in ("draft", "info_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Documents cannot be uploaded when application status is '{application.status}'. Uploads are permitted only in 'draft' or 'info_requested' status."
        )

    # Validate and save file securely
    val_result = await validate_and_save_upload(file)
    if not val_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=val_result.error_message
        )

    # Compute pHash
    phash = compute_phash_for_file(val_result.storage_rel_path, val_result.mime_type)

    document = Document(
        application_id=application.id,
        doc_type=doc_type,
        original_filename=val_result.sanitized_filename,
        stored_path=val_result.storage_rel_path,
        mime_type=val_result.mime_type,
        size=os.path.getsize(val_result.storage_rel_path),
        sha256=val_result.sha256,
        phash=phash,
        page_count=val_result.page_count,
        processing_status="queued",
        processing_stage="Queued",
        validation_status="pending_processing"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Supersede previous active document of the same type for this application
    previous_docs = db.query(Document).filter(
        Document.application_id == application.id,
        Document.doc_type == doc_type,
        Document.id != document.id,
        Document.superseded_by.is_(None)
    ).all()
    for prev in previous_docs:
        prev.superseded_by = document.id
    if previous_docs:
        db.commit()

    record_audit_event(
        db=db,
        action="document_uploaded",
        entity_type="document",
        entity_id=document.id,
        actor=current_user,
        after_state={
            "filename": document.original_filename,
            "doc_type": document.doc_type,
            "sha256": document.sha256
        }
    )

    # Trigger async processing pipeline
    background_tasks.add_task(process_document_pipeline, document.id)

    return document

@router.post("/documents/{document_id}/reprocess", response_model=DocumentOut)
def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    verify_institution_access(current_user, document.application.institution_id)

    document.processing_status = "queued"
    document.processing_stage = "Queued for Reprocessing"
    document.processing_error = None
    document.validation_status = "pending_processing"
    db.commit()

    record_audit_event(
        db=db,
        action="document_reprocess_triggered",
        entity_type="document",
        entity_id=document.id,
        actor=current_user,
        after_state={"processing_status": "queued"}
    )

    background_tasks.add_task(process_document_pipeline, document.id)
    return document

@router.get("/applications/{application_id}/documents-detailed", response_model=list[DocumentOut])
def get_application_documents_detailed(
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
    return docs

@router.patch("/extracted-fields/{field_id}", response_model=ExtractedFieldOut)
def correct_extracted_field(
    field_id: int,
    payload: FieldUpdate,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Officials can correct low-confidence or wrongly extracted values with mandatory audit logging."""
    field = db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extracted field not found")

    before_val = field.edited_value if field.edited_value is not None else field.value
    field.edited_value = payload.value
    field.edited_by = current_user.id
    field.needs_review = False

    record_audit_event(
        db=db,
        action="field_corrected_by_official",
        entity_type="extracted_field",
        entity_id=field.id,
        actor=current_user,
        before_state={"value": before_val},
        after_state={"edited_value": payload.value, "remarks": payload.remarks}
    )

    db.commit()
    db.refresh(field)
    return field

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    application = document.application
    verify_institution_access(current_user, application.institution_id)

    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officials cannot delete applicant-submitted documents."
        )

    if application.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documents can only be deleted while application is in 'draft' status."
        )

    record_audit_event(
        db=db,
        action="document_deleted",
        entity_type="document",
        entity_id=document.id,
        actor=current_user,
        before_state={"filename": document.original_filename, "doc_type": document.doc_type}
    )

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}

def resolve_stored_path(stored_path: str) -> Path:
    p = Path(stored_path)
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p.resolve()
    storage_root = Path(settings.STORAGE_DIR).resolve()
    cand = storage_root / p.name
    if cand.exists():
        return cand
    cand2 = storage_root.parent / stored_path
    if cand2.exists():
        return cand2.resolve()
    return p

@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    verify_institution_access(current_user, document.application.institution_id)

    file_path = resolve_stored_path(document.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=document.mime_type or "application/octet-stream",
        filename=document.original_filename,
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"}
    )

@router.get("/documents/{document_id}/page/{page_number}/image")
def get_document_page_image(
    document_id: int,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if page_number < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page number must be 1 or greater")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    verify_institution_access(current_user, document.application.institution_id)

    file_path = resolve_stored_path(document.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found on disk")

    derived_dir = Path(settings.DERIVED_DIR)
    derived_dir.mkdir(parents=True, exist_ok=True)
    cached_page_path = derived_dir / f"doc_{document.id}_page_{page_number}.png"

    if cached_page_path.exists():
        return FileResponse(
            path=str(cached_page_path),
            media_type="image/png",
            filename=f"doc_{document.id}_page_{page_number}.png",
            content_disposition_type="inline"
        )

    mime = (document.mime_type or "").lower()
    try:
        if "pdf" in mime:
            doc = fitz.open(str(file_path))
            idx = page_number - 1
            if idx < 0 or idx >= len(doc):
                total = len(doc)
                doc.close()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Page {page_number} out of range (document has {total} pages)")
            pix = doc[idx].get_pixmap(dpi=150)
            pix.save(str(cached_page_path))
            doc.close()
        else:
            if page_number > 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Page {page_number} out of range for single-page image")
            with Image.open(str(file_path)) as img:
                img.save(str(cached_page_path), "PNG")
    except HTTPException:
        raise
    except Exception as e:
        # Resilient fallback: attempt cross-format decoding
        try:
            with Image.open(str(file_path)) as img:
                img.save(str(cached_page_path), "PNG")
        except Exception:
            try:
                doc = fitz.open(str(file_path))
                idx = page_number - 1
                if 0 <= idx < len(doc):
                    pix = doc[idx].get_pixmap(dpi=150)
                    pix.save(str(cached_page_path))
                    doc.close()
                else:
                    doc.close()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Page {page_number} out of range")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to render page image: {str(e)}")

    return FileResponse(
        path=str(cached_page_path),
        media_type="image/png",
        filename=f"doc_{document.id}_page_{page_number}.png",
        content_disposition_type="inline"
    )

@router.get("/documents/{document_id}/ela")
def get_document_ela_heatmap(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    verify_institution_access(current_user, document.application.institution_id)

    if current_user.role == "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Internal forensic ELA heatmaps are restricted to council scrutiny officials."
        )

    file_path = resolve_stored_path(document.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found on disk")

    derived_dir = Path(settings.DERIVED_DIR)
    derived_dir.mkdir(parents=True, exist_ok=True)
    ela_path = derived_dir / f"ela_doc_{document.id}.png"

    if ela_path.exists():
        return FileResponse(
            path=str(ela_path),
            media_type="image/png",
            filename=f"ela_doc_{document.id}.png",
            content_disposition_type="inline"
        )

    # Generate ELA on-the-fly
    from backend.app.engines.forensics_image import analyze_image_forensics
    analyze_image_forensics(str(file_path), document.mime_type, document.id)

    if ela_path.exists():
        return FileResponse(
            path=str(ela_path),
            media_type="image/png",
            filename=f"ela_doc_{document.id}.png",
            content_disposition_type="inline"
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ELA heatmap unavailable for this document")

@router.post("/documents/{document_id}/official-review", response_model=DocumentOut)
def record_official_document_review(
    document_id: int,
    payload: OfficialDocumentReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Authorised Scrutiny Officer records a document-level review determination.
    Distinct statuses:
    - verified: Officer verified content matches requirements
    - mismatch_confirmed: Confirmed discrepancy noted (does not auto-reject app)
    - unable_to_verify: Unclear/incomplete evidence noted
    - pending_review: Reset to pending
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    valid_outcomes = [
        "verified",
        "rejected",
        "mismatch_confirmed",
        "requires_correction",
        "more_information_required",
        "unable_to_verify",
        "pending_review"
    ]
    outcome_lower = payload.outcome.lower()
    if outcome_lower not in valid_outcomes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review outcome '{payload.outcome}'. Must be one of: {valid_outcomes}"
        )

    if outcome_lower in ("rejected", "mismatch_confirmed", "requires_correction", "more_information_required", "unable_to_verify"):
        if not payload.remarks or len(payload.remarks.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Substantive officer explanation (min 5 characters) is mandatory when recording {payload.outcome}."
            )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    doc.official_verification_status = outcome_lower
    doc.official_verification_remarks = payload.remarks.strip() if payload.remarks else None
    doc.official_verified_by = current_user.id
    doc.official_verified_at = now

    # Update or resolve internal finding flags based on determination
    from backend.app.models.finding import Flag
    if outcome_lower in ("rejected", "mismatch_confirmed"):
        scrutiny_flag = db.query(Flag).filter(
            Flag.application_id == doc.application_id,
            Flag.document_id == doc.id,
            Flag.category == "mismatch"
        ).first()
        if not scrutiny_flag:
            db.add(Flag(
                application_id=doc.application_id,
                document_id=doc.id,
                category="mismatch",
                severity="critical",
                title=f"Official Scrutiny Rejection: {doc.doc_type.replace('_', ' ').title()}",
                explanation=payload.remarks.strip(),
                evidence={"document_id": doc.id, "field_name": payload.field_name, "determination": outcome_lower},
                confidence=1.0,
                confidence_meaning="Authorised officer scrutiny review determination",
                actionability="INTERNAL_REVIEW_ONLY",
                status="open"
            ))
        else:
            scrutiny_flag.explanation = payload.remarks.strip()
            scrutiny_flag.status = "open"
    elif outcome_lower == "verified":
        scrutiny_flag = db.query(Flag).filter(
            Flag.application_id == doc.application_id,
            Flag.document_id == doc.id,
            Flag.category == "mismatch"
        ).first()
        if scrutiny_flag:
            scrutiny_flag.status = "acknowledged"

    record_audit_event(
        db=db,
        action="OFFICIAL_DOCUMENT_REVIEW",
        entity_type="document",
        entity_id=doc.id,
        actor=current_user,
        after_state={
            "official_verification_status": doc.official_verification_status,
            "remarks": doc.official_verification_remarks,
            "field_name": payload.field_name
        }
    )

    db.commit()
    db.refresh(doc)
    return doc

@router.post("/documents/{document_id}/re-validate")
def revalidate_document_content(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official)
):
    """
    Re-evaluates automated validation checks and consistency rules for a document.
    """
    from backend.app.engines.validator import validate_document_content

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    fields = {
        f.key: (f.edited_value if f.edited_value is not None else f.value)
        for f in doc.extracted_fields
    }
    decl = doc.application.declared_details or {}

    val_flags = validate_document_content(
        doc_type=doc.doc_type,
        extracted_fields=fields,
        declared_details=decl,
        page_count=doc.page_count
    )

    has_critical = any(f.get("severity") == "critical" for f in val_flags)
    has_warning = any(f.get("severity") == "warning" for f in val_flags)

    if doc.processing_status in ("queued", "processing"):
        doc.validation_status = "pending_processing"
    elif doc.processing_status == "failed":
        doc.validation_status = "unable_to_verify"
    elif any(f.get("category") == "expired" for f in val_flags):
        doc.validation_status = "expired"
    elif has_critical:
        doc.validation_status = "incomplete"
    elif has_warning:
        doc.validation_status = "review_required"
    else:
        doc.validation_status = "valid"

    record_audit_event(
        db=db,
        action="DOCUMENT_REVALIDATED",
        entity_type="document",
        entity_id=doc.id,
        actor=current_user,
        after_state={
            "validation_status": doc.validation_status,
            "flags_count": len(val_flags)
        }
    )

    db.commit()
    db.refresh(doc)
    return {
        "document_id": doc.id,
        "validation_status": doc.validation_status,
        "official_verification_status": doc.official_verification_status,
        "flags_count": len(val_flags),
        "flags": val_flags
    }

