import os
import traceback
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, ExtractedField
from backend.app.models.finding import Flag
from backend.app.engines.ocr import extract_text_from_document
from backend.app.engines.classifier import classify_document
from backend.app.engines.extractor import extract_fields_from_text
from backend.app.services.audit import record_audit_event

def process_document_pipeline(document_id: int):
    """
    Synchronous / Background worker function for document processing.
    Runs OCR extraction, classification, and field extraction.
    Updates Document stages for frontend polling.
    """
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.processing_status = "processing"
        doc.processing_stage = "Extracting Text"
        doc.processing_error = None
        db.commit()

        # 1. OCR & Text Extraction
        ocr_result = extract_text_from_document(
            file_path=doc.stored_path,
            mime_type=doc.mime_type,
            max_pages=doc.page_count
        )
        full_text = ocr_result.get("full_text", "")
        pages_data = ocr_result.get("pages", [])
        quality_flags = ocr_result.get("quality_flags", [])

        # Store any quality warnings as review flags
        for qf in quality_flags:
            exists = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == "quality",
                Flag.title == qf["title"]
            ).first()
            if not exists:
                flag = Flag(
                    application_id=doc.application_id,
                    document_id=doc.id,
                    category="quality",
                    severity=qf["severity"],
                    title=qf["title"],
                    explanation=qf["explanation"],
                    evidence={"quality_metrics": qf},
                    confidence=qf["confidence"],
                    confidence_meaning="Image Laplacian variance and resolution heuristic check",
                    status="open"
                )
                db.add(flag)

        # 2. Document Classification
        doc.processing_stage = "Identifying Document Type"
        db.commit()

        class_result = classify_document(
            text=full_text,
            filename=doc.original_filename,
            uploaded_slot=doc.doc_type
        )

        # Handle classification mismatch flag if detected
        if class_result.mismatch_flag:
            mf = class_result.mismatch_flag
            exists_mismatch = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == "mismatch",
                Flag.title == mf["title"]
            ).first()
            if not exists_mismatch:
                mismatch_flag = Flag(
                    application_id=doc.application_id,
                    document_id=doc.id,
                    category="mismatch",
                    severity=mf["severity"],
                    title=mf["title"],
                    explanation=mf["explanation"],
                    evidence=mf["evidence"],
                    confidence=mf["confidence"],
                    confidence_meaning=mf["confidence_meaning"],
                    status="open"
                )
                db.add(mismatch_flag)

        # 3. Field Extraction
        doc.processing_stage = "Extracting Key Information"
        db.commit()

        extracted_fields_data = extract_fields_from_text(
            full_text=full_text,
            doc_type=doc.doc_type,
            pages_data=pages_data
        )

        # Clear any existing fields for this doc before inserting new ones
        db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()

        for field_dict in extracted_fields_data:
            ef = ExtractedField(
                document_id=doc.id,
                key=field_dict["key"],
                value=field_dict["value"],
                ocr_confidence=field_dict["ocr_confidence"],
                extraction_method=field_dict["extraction_method"],
                page=field_dict["page"],
                bbox=field_dict["bbox"],
                needs_review=field_dict["needs_review"]
            )
            db.add(ef)

        # 4. Pipeline Completion
        doc.processing_status = "completed"
        doc.processing_stage = "Completed"
        db.commit()

        record_audit_event(
            db=db,
            action="pipeline_completed",
            entity_type="document",
            entity_id=doc.id,
            actor=None,
            after_state={
                "fields_extracted": len(extracted_fields_data),
                "classified_as": class_result.doc_type,
                "confidence": class_result.confidence
            }
        )

    except Exception as e:
        db.rollback()
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.processing_stage = "Failed"
            doc.processing_error = str(e)[:900]
            db.commit()
    finally:
        db.close()
