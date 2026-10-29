import os
import shutil
import uuid
import hashlib
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
import fitz

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.institution import Institution
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.verification import VerificationResult
from backend.app.pipeline.orchestrator import process_document_pipeline
from backend.app.routers.documents import compute_phash_for_file
from backend.app.routers.findings import sync_validation_and_consistency
from backend.app.engines.verifiers import verify_document
from backend.app.engines.compliance import ComplianceEngine
from backend.app.engines.risk import RiskEngine

def get_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    return "application/octet-stream"

def seed_sample_scenarios(db: Optional[Session] = None):
    """
    Imports and processes synthetic sample scenarios A through I into the database.
    Idempotent: skips applications that are already seeded and processed.
    """
    owns_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        owns_db = True

    try:
        base_sample_dir = Path(__file__).resolve().parent.parent.parent / "sample_data"
        if not base_sample_dir.exists():
            print(f"[WARN] sample_data directory not found at {base_sample_dir}")
            return

        # Ensure institutions exist
        inst_apex = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
        inst_zenith = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1002").first()

        if not inst_apex or not inst_zenith:
            print("[INFO] Institutions not found. Seeding core institutions first...")
            from backend.scripts.seed_db import seed_database
            seed_database(db_session=db)
            inst_apex = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
            inst_zenith = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1002").first()

        storage_dir = Path(settings.STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)

        scenarios_config = [
            {
                "key": "scenario_A",
                "app_no": "APP-2025-SCEN-A",
                "institution_id": inst_apex.id,
                "folder": "scenario_A_pristine",
                "declared_details": {
                    "institution_name": "Apex Institute of Technology",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 42/1A",
                    "land_area_acres": 3.5,
                    "built_up_area_sqm": 4500.0,
                    "program": "Engineering",
                    "faculty_count": 60,
                    "student_enrollment": 300,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_B",
                "app_no": "APP-2025-SCEN-B",
                "institution_id": inst_zenith.id,
                "folder": "scenario_B_missing_doc",
                "declared_details": {
                    "institution_name": "Bharati Technical Campus",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 12/4B",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 240,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                    # Fire NOC intentionally omitted to exercise missing document detection
                ]
            },
            {
                "key": "scenario_C",
                "app_no": "APP-2025-SCEN-C",
                "institution_id": inst_zenith.id,
                "folder": "scenario_C_expired_noc",
                "declared_details": {
                    "institution_name": "Zenith Polytechnic",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 55/2A",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 4100.0,
                    "program": "Engineering",
                    "faculty_count": 45,
                    "student_enrollment": 200,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc_expired.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_D",
                "app_no": "APP-2025-SCEN-D",
                "institution_id": inst_apex.id,
                "folder": "scenario_D_area_mismatch",
                "declared_details": {
                    "institution_name": "Kaveri Engineering Institute",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 89/1C",
                    "land_area_acres": 4.5,
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 55,
                    "student_enrollment": 250,
                },
                "documents": [
                    {"filename": "title_deed_mismatch.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_E",
                "app_no": "APP-2025-SCEN-E",
                "institution_id": inst_zenith.id,
                "folder": "scenario_E_duplicate",
                "declared_details": {
                    "institution_name": "Zenith Satellite Campus",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 42/1A",
                    "land_area_acres": 3.5,
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 240,
                },
                "documents": [
                    {"filename": "duplicate_title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_F",
                "app_no": "APP-2025-SCEN-F",
                "institution_id": inst_apex.id,
                "folder": "scenario_F_tampered",
                "declared_details": {
                    "institution_name": "Apex Vocational Wing",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Plot 88/B",
                    "land_area_acres": 5.5,
                    "built_up_area_sqm": 4000.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 200,
                },
                "documents": [
                    {"filename": "tampered_land_record.jpg", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_G",
                "app_no": "APP-2025-SCEN-G",
                "institution_id": inst_apex.id,
                "folder": "scenario_G_non_compliant",
                "declared_details": {
                    "institution_name": "Himalayan Institute",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 101/A",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 2800.0,
                    "program": "Engineering",
                    "faculty_count": 60,
                    "student_enrollment": 360,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan_deficit.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_H",
                "app_no": "APP-2025-SCEN-H",
                "institution_id": inst_apex.id,
                "folder": "scenario_H_auth_rejection",
                "declared_details": {
                    "institution_name": "Saraswati Technical College",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 202/B",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 4000.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 250,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc_rejected.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_I1",
                "app_no": "APP-2025-SCEN-I1",
                "institution_id": inst_apex.id,
                "folder": "scenario_I_template_sharing",
                "declared_details": {
                    "institution_name": "Delhi College of Engineering",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 301/C",
                    "land_area_acres": 3.2,
                    "built_up_area_sqm": 4100.0,
                    "program": "Engineering",
                    "faculty_count": 55,
                    "student_enrollment": 260,
                },
                "documents": [
                    {"filename": "title_deed_college_1.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan_college_1.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc_college_1.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration_college_1.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit_college_1.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "scenario_I2",
                "app_no": "APP-2025-SCEN-I2",
                "institution_id": inst_zenith.id,
                "folder": "scenario_I_template_sharing",
                "declared_details": {
                    "institution_name": "Mumbai Technical Institute",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 402/D",
                    "land_area_acres": 3.1,
                    "built_up_area_sqm": 4150.0,
                    "program": "Engineering",
                    "faculty_count": 55,
                    "student_enrollment": 260,
                },
                "documents": [
                    {"filename": "title_deed_college_2.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan_college_2.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc_college_2.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration_college_2.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit_college_2.pdf", "doc_type": "affidavit"},
                ]
            },
        ]

        for sc in scenarios_config:
            app_no = sc["app_no"]
            app = db.query(Application).filter(Application.application_no == app_no).first()

            if not app:
                app = Application(
                    application_no=app_no,
                    institution_id=sc["institution_id"],
                    type="New Technical Institution",
                    academic_year="2025-2026",
                    status="under_verification",
                    risk_score=0.0,
                    risk_band="Low",
                    risk_breakdown={},
                    declared_details=sc["declared_details"],
                )
                db.add(app)
                db.commit()
                db.refresh(app)
                print(f"[SEED] Created application {app_no} (ID: {app.id})")
            else:
                print(f"[SEED] Application {app_no} already exists (ID: {app.id})")

            created_doc_ids = []
            for doc_spec in sc["documents"]:
                existing_doc = db.query(Document).filter(
                    Document.application_id == app.id,
                    Document.doc_type == doc_spec["doc_type"],
                    Document.superseded_by.is_(None)
                ).first()

                src_path = base_sample_dir / sc["folder"] / doc_spec["filename"]
                if not src_path.exists():
                    print(f"  [WARN] File not found: {src_path}")
                    continue

                if existing_doc:
                    if not Path(existing_doc.stored_path).exists():
                        shutil.copy2(src_path, existing_doc.stored_path)
                        print(f"  [SEED] Restored missing file on disk for Doc ID {existing_doc.id}")
                    continue

                file_ext = src_path.suffix.lower()
                target_filename = f"{uuid.uuid4().hex}{file_ext}"
                dest_path = storage_dir / target_filename
                shutil.copy2(src_path, dest_path)

                with open(dest_path, "rb") as f:
                    file_bytes = f.read()
                    sha256 = hashlib.sha256(file_bytes).hexdigest()

                mime_type = get_mime_type(src_path.name)
                phash = compute_phash_for_file(str(dest_path), mime_type)

                page_count = 1
                if "pdf" in mime_type:
                    try:
                        pdf_doc = fitz.open(str(dest_path))
                        page_count = len(pdf_doc)
                        pdf_doc.close()
                    except Exception:
                        page_count = 1

                doc = Document(
                    application_id=app.id,
                    doc_type=doc_spec["doc_type"],
                    original_filename=doc_spec["filename"],
                    stored_path=str(dest_path),
                    mime_type=mime_type,
                    size=len(file_bytes),
                    sha256=sha256,
                    phash=phash,
                    page_count=page_count,
                    processing_status="queued",
                    processing_stage="Queued",
                    validation_status="valid"
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                created_doc_ids.append(doc.id)
                print(f"  [SEED] Ingested document: {doc_spec['filename']} -> Doc ID {doc.id}")

            # Process pipeline for each newly created document synchronously
            for doc_id in created_doc_ids:
                print(f"  [PIPE] Processing pipeline for Doc ID {doc_id}...")
                process_document_pipeline(doc_id)

            # Re-query documents for validation & verifications
            db.refresh(app)

            # Run document checklist validation and consistency engine
            sync_validation_and_consistency(app.id, db)

            # Run authority verifications for documents without existing results
            docs = db.query(Document).filter(
                Document.application_id == app.id,
                Document.superseded_by.is_(None)
            ).all()

            for d in docs:
                has_vr = db.query(VerificationResult).filter(VerificationResult.document_id == d.id).first()
                if not has_vr:
                    extracted = d.extracted_data or {}
                    ref_no = (
                        extracted.get("reference_no") or
                        extracted.get("sanction_no") or
                        extracted.get("noc_number") or
                        extracted.get("registration_no") or
                        extracted.get("order_no")
                    )
                    outcome = verify_document(doc_type=d.doc_type, reference_no=ref_no, document_context=extracted)
                    v_res = VerificationResult(
                        document_id=d.id,
                        authority=outcome.authority,
                        adapter_name=outcome.adapter_name,
                        reference_no=outcome.reference_no,
                        status=outcome.status,
                        is_simulated=True,
                        raw_response=outcome.raw_response,
                        message=outcome.message
                    )
                    db.add(v_res)
            db.commit()

            # Run compliance engine
            ComplianceEngine(db).evaluate_application(app.id)

            # Run risk engine to compute score and review band
            risk_info = RiskEngine(db).calculate_application_risk(app.id)

            # Set workflow status based on risk and findings
            if risk_info["score"] >= 25 or risk_info["critical_flags_count"] > 0:
                app.status = "needs_review"
            else:
                app.status = "under_verification"
            db.commit()
            print(f"  [DONE] App {app_no}: Risk {risk_info['score']}/100 ({risk_info['band']}) -> Status: {app.status}")

        print("\n[SUCCESS] All synthetic scenario applications and documents successfully seeded and processed.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed sample scenarios: {e}")
        raise e
    finally:
        if owns_db:
            db.close()

if __name__ == "__main__":
    seed_sample_scenarios()
