import os
import traceback
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.application import Application
from backend.app.models.document import Document, ExtractedField
from backend.app.models.finding import Flag
from backend.app.engines.ocr import extract_text_from_document
from backend.app.engines.classifier import classify_document
from backend.app.engines.extractor import extract_fields_from_text
from backend.app.engines.forensics_image import analyze_image_forensics
from backend.app.engines.forensics_pdf import analyze_pdf_forensics
from backend.app.engines.duplicates import check_document_duplicates
from backend.app.services.audit import record_audit_event

def process_document_pipeline(document_id: int):
    """
    Synchronous / Background worker function for document processing.
    Runs:
    1. OCR & Quality Checks
    2. Document Classification & Slot Mismatch check
    3. Parameter Extraction & BBox Mapping
    4. Image Forensics (ELA & Copy-Move)
    5. PDF Metadata Forensics
    6. Exact & Near Duplicate Detection with Template Awareness
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

        # Store quality flags
        for qf in quality_flags:
            exists = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == "quality",
                Flag.title == qf["title"]
            ).first()
            if not exists:
                db.add(Flag(
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
                ))

        # 2. Document Classification
        doc.processing_stage = "Identifying Document Type"
        db.commit()

        class_result = classify_document(
            text=full_text,
            filename=doc.original_filename,
            uploaded_slot=doc.doc_type
        )

        if class_result.mismatch_flag:
            mf = class_result.mismatch_flag
            exists_mismatch = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == "mismatch",
                Flag.title == mf["title"]
            ).first()
            if not exists_mismatch:
                db.add(Flag(
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
                ))

        # 3. Field Extraction
        doc.processing_stage = "Extracting Key Information"
        db.commit()

        extracted_fields_data = extract_fields_from_text(
            full_text=full_text,
            doc_type=doc.doc_type,
            pages_data=pages_data
        )

        db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
        curr_fields_dict = {}
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
            curr_fields_dict[field_dict["key"]] = field_dict["value"]

        db.commit()

        # 4. Forensic Signals (ELA, Copy-Move & PDF Metadata)
        doc.processing_stage = "Running Forensic Analysis"
        db.commit()

        forensic_flags = []
        # Image forensics
        img_flags = analyze_image_forensics(
            file_path=doc.stored_path,
            mime_type=doc.mime_type,
            document_id=doc.id
        )
        forensic_flags.extend(img_flags)

        # PDF metadata forensics
        if "pdf" in doc.mime_type:
            pdf_flags = analyze_pdf_forensics(doc.stored_path, doc.id)
            forensic_flags.extend(pdf_flags)

        for ff in forensic_flags:
            exists_ff = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == ff["category"],
                Flag.title == ff["title"]
            ).first()
            if not exists_ff:
                db.add(Flag(
                    application_id=doc.application_id,
                    document_id=doc.id,
                    category=ff["category"],
                    severity=ff["severity"],
                    title=ff["title"],
                    explanation=ff["explanation"],
                    evidence=ff["evidence"],
                    bbox=ff.get("bbox"),
                    confidence=ff["confidence"],
                    confidence_meaning=ff["confidence_meaning"],
                    rule_ref=ff.get("rule_ref"),
                    status="open"
                ))

        # 5. Duplicate Detection (Cross-Institution & Intra-Application)
        candidate_docs_db = db.query(Document).join(Application, Document.application_id == Application.id).filter(
            Document.id != doc.id,
            Document.superseded_by.is_(None)
        ).all()

        cand_list = []
        cand_fields_map = {}
        for cd in candidate_docs_db:
            cand_list.append({
                "id": cd.id,
                "doc_type": cd.doc_type,
                "original_filename": cd.original_filename,
                "sha256": cd.sha256,
                "phash": cd.phash,
                "institution_id": cd.application.institution_id
            })
            cd_fields = db.query(ExtractedField).filter(ExtractedField.document_id == cd.id).all()
            cand_fields_map[cd.id] = {cf.key: cf.value for cf in cd_fields if cf.value}

        dup_flags = check_document_duplicates(
            current_doc={
                "id": doc.id,
                "doc_type": doc.doc_type,
                "original_filename": doc.original_filename,
                "sha256": doc.sha256,
                "phash": doc.phash
            },
            candidate_docs=cand_list,
            current_fields=curr_fields_dict,
            candidate_fields_by_doc=cand_fields_map,
            current_institution_id=doc.application.institution_id
        )

        for df in dup_flags:
            exists_dup = db.query(Flag).filter(
                Flag.document_id == doc.id,
                Flag.category == "duplicate",
                Flag.title == df["title"]
            ).first()
            if not exists_dup:
                db.add(Flag(
                    application_id=doc.application_id,
                    document_id=doc.id,
                    related_document_id=df["evidence"].get("matched_doc_id"),
                    category="duplicate",
                    severity=df["severity"],
                    title=df["title"],
                    explanation=df["explanation"],
                    evidence=df["evidence"],
                    confidence=df["confidence"],
                    confidence_meaning=df["confidence_meaning"],
                    rule_ref=df.get("rule_ref"),
                    status="open"
                ))

        # 6. Pipeline Completion
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
                "fields_count": len(extracted_fields_data),
                "forensic_flags_count": len(forensic_flags),
                "duplicate_flags_count": len(dup_flags)
            }
        )

    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.processing_stage = "Failed"
            doc.processing_error = str(e)[:900]
            db.commit()
    finally:
        db.close()
