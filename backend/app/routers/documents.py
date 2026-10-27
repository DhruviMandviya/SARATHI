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
from backend.app.schemas.document import DocumentOut, ExtractedFieldOut, FieldUpdate
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
        validation_status="valid"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

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

    if not os.path.exists(document.stored_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found on disk")

    return FileResponse(
        path=document.stored_path,
        media_type=document.mime_type,
        filename=document.original_filename
    )

@router.get("/documents/{document_id}/page/{page_number}/image")
def get_document_page_image(
    document_id: int,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    verify_institution_access(current_user, document.application.institution_id)

    derived_dir = Path(settings.DERIVED_DIR)
    derived_dir.mkdir(parents=True, exist_ok=True)
    cached_page_path = derived_dir / f"doc_{document.id}_page_{page_number}.png"

    if cached_page_path.exists():
        return FileResponse(path=str(cached_page_path), media_type="image/png")

    if not os.path.exists(document.stored_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")

    try:
        if "pdf" in document.mime_type:
            doc = fitz.open(document.stored_path)
            idx = page_number - 1
            if idx < 0 or idx >= len(doc):
                doc.close()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Page {page_number} out of range")
            pix = doc[idx].get_pixmap(dpi=150)
            pix.save(str(cached_page_path))
            doc.close()
        else:
            with Image.open(document.stored_path) as img:
                img.save(str(cached_page_path), "PNG")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to render page: {str(e)}")

    return FileResponse(path=str(cached_page_path), media_type="image/png")
