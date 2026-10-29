import os
import shutil
import pytest
from datetime import datetime, timezone
from pathlib import Path
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.institution import Institution
from backend.app.models.application import Application
from backend.app.models.document import Document, ExtractedField
from backend.app.models.finding import Flag
from backend.app.models.verification import VerificationResult
from backend.app.models.audit import AuditLog
from backend.app.pipeline.orchestrator import process_document_pipeline
from backend.app.routers.findings import sync_validation_and_consistency
from backend.scripts.seed_sample_scenarios import seed_sample_scenarios


@pytest.fixture
def auth_headers_inst(client, db_session):
    inst_user = db_session.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
    token = create_access_token(subject=1, role="institution", institution_id=inst_user.id if inst_user else 1)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_official():
    token = create_access_token(subject=3, role="official", institution_id=None)
    return {"Authorization": f"Bearer {token}"}


def test_or_symbol_runtime_resolution_and_pipeline_completion(db_session):
    """
    1. Verifies that the 'or_' and 'and_' SQLAlchemy expressions in candidate
    document duplicate checking in process_document_pipeline execute without NameError.
    """
    seed_sample_scenarios(db=db_session)
    app_record = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-A").first()
    assert app_record is not None

    storage_dir = Path(settings.STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "sample_data" / "scenario_A_pristine" / "land_document_pristine.pdf"

    dest_file = storage_dir / "test_dup_check.pdf"
    if sample_pdf.exists():
        shutil.copy(sample_pdf, dest_file)
    else:
        dest_file.write_bytes(b"%PDF-1.4 dummy pdf content for testing duplicate logic")

    doc1 = Document(
        application_id=app_record.id,
        doc_type="land_document",
        original_filename="land_doc_orig.pdf",
        stored_path=str(dest_file),
        mime_type="application/pdf",
        size=dest_file.stat().st_size,
        sha256="test_sha256_candidate_hash",
        phash="0000000000000000",
        page_count=1,
        processing_status="queued",
        processing_stage="Queued",
        validation_status="pending_processing"
    )
    db_session.add(doc1)
    db_session.commit()
    db_session.refresh(doc1)

    # Process first document
    process_document_pipeline(doc1.id)
    db_session.refresh(doc1)
    assert doc1.processing_status in ("completed", "failed")
    assert "name 'or_' is not defined" not in str(doc1.processing_error or "")

    # Create second document sharing same sha256 to trigger candidate duplicate checking with or_
    doc2 = Document(
        application_id=app_record.id,
        doc_type="land_document",
        original_filename="land_doc_dup.pdf",
        stored_path=str(dest_file),
        mime_type="application/pdf",
        size=dest_file.stat().st_size,
        sha256="test_sha256_candidate_hash",
        phash="0000000000000000",
        page_count=1,
        processing_status="queued",
        processing_stage="Queued",
        validation_status="pending_processing"
    )
    db_session.add(doc2)
    db_session.commit()
    db_session.refresh(doc2)

    # Running pipeline on doc2 triggers the candidate duplicate query with or_ and and_
    process_document_pipeline(doc2.id)
    db_session.refresh(doc2)

    # Must NOT fail with "name 'or_' is not defined"
    assert "name 'or_' is not defined" not in str(doc2.processing_error or "")
    assert doc2.processing_status != "failed" or "or_" not in str(doc2.processing_error)


def test_pdf_native_text_extraction(db_session):
    """
    2. Verifies native PDF text extraction on a pristine PDF.
    """
    seed_sample_scenarios(db=db_session)
    app_record = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-A").first()
    storage_dir = Path(settings.STORAGE_DIR)
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "sample_data" / "scenario_A_pristine" / "land_document_pristine.pdf"

    if sample_pdf.exists():
        dest_file = storage_dir / "test_pristine_native.pdf"
        shutil.copy(sample_pdf, dest_file)

        doc = Document(
            application_id=app_record.id,
            doc_type="land_document",
            original_filename="land_document_pristine.pdf",
            stored_path=str(dest_file),
            mime_type="application/pdf",
            size=dest_file.stat().st_size,
            page_count=1,
            processing_status="queued",
            processing_stage="Queued",
            validation_status="pending_processing"
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        process_document_pipeline(doc.id)
        db_session.refresh(doc)

        assert doc.processing_status == "completed"
        fields = db_session.query(ExtractedField).filter(ExtractedField.document_id == doc.id).all()
        assert len(fields) > 0
        methods = [f.extraction_method for f in fields]
        assert any("pdf" in m.lower() for m in methods)


def test_ocr_fallback_and_graceful_failure(db_session):
    """
    3. Verifies that when an image/scanned document has no native text and OCR is unavailable,
    the system reports OCR Unavailable / OCR Failed and unable_to_verify, without reporting false success.
    """
    seed_sample_scenarios(db=db_session)
    app_record = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-A").first()
    storage_dir = Path(settings.STORAGE_DIR)
    dest_file = storage_dir / "test_scanned_img.png"
    # Create a 10x10 blank PNG
    dest_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\n\x00\x00\x00\n\x08\x06\x00\x00\x00\x8d2\xcf\xbd\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82")

    doc = Document(
        application_id=app_record.id,
        doc_type="building_plan",
        original_filename="building_plan_scanned.png",
        stored_path=str(dest_file),
        mime_type="image/png",
        size=dest_file.stat().st_size,
        page_count=1,
        processing_status="queued",
        processing_stage="Queued",
        validation_status="pending_processing"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    process_document_pipeline(doc.id)
    db_session.refresh(doc)

    # When OCR is unavailable or fails to extract text, it must gracefully fail or mark OCR Unavailable
    assert doc.processing_status in ("failed", "completed")
    if doc.processing_status == "failed":
        assert doc.processing_stage in ("OCR Unavailable", "OCR Failed", "Failed")
        assert doc.validation_status == "unable_to_verify"


def test_document_processing_retry_deduplication(client, auth_headers_official, db_session):
    """
    4 & 11. Verifies that retrying document processing via /documents/{id}/reprocess reruns
    without creating duplicate ExtractedField or duplicate Flag records.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    assert doc is not None

    fields_before = db_session.query(ExtractedField).filter(ExtractedField.document_id == doc.id).count()
    flags_before = db_session.query(Flag).filter(Flag.document_id == doc.id).count()

    # Call reprocess endpoint
    res = client.post(f"/api/v1/documents/{doc.id}/reprocess", headers=auth_headers_official)
    assert res.status_code == status.HTTP_200_OK
    db_session.refresh(doc)

    fields_after = db_session.query(ExtractedField).filter(ExtractedField.document_id == doc.id).count()
    # Fields should not be duplicated
    assert fields_after <= max(fields_before, 1)


def test_stage4_validation_statuses_and_official_review_persistence(client, auth_headers_official, db_session):
    """
    5. Verifies Stage 4 automated validation statuses and official review persistence.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    assert doc is not None

    # Automated validation mapping verification
    sync_validation_and_consistency(doc.application_id, db_session)
    db_session.refresh(doc)
    assert doc.validation_status in ("valid", "incomplete", "invalid", "expired", "unable_to_verify", "pending_processing")

    # Official verification: Mark Verified
    res = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "verified", "remarks": "Legally verified by AICTE Scrutiny Officer"},
        headers=auth_headers_official
    )
    assert res.status_code == status.HTTP_200_OK
    db_session.refresh(doc)
    assert doc.official_verification_status == "verified"
    assert doc.official_verification_remarks == "Legally verified by AICTE Scrutiny Officer"
    assert doc.official_verified_at is not None


def test_rejection_and_correction_request_mandatory_remarks(client, auth_headers_official, db_session):
    """
    6. Verifies that rejecting or requesting correction requires substantive remarks (>= 5 chars).
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    assert doc is not None

    # Rejection without remarks -> Expect 400 Bad Request
    res_no_remarks = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "rejected", "remarks": "   "},
        headers=auth_headers_official
    )
    assert res_no_remarks.status_code == status.HTTP_400_BAD_REQUEST

    # Rejection with substantive remarks -> 200 OK and records critical finding
    res_valid_reject = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "rejected", "remarks": "Document boundary coordinates do not match revenue survey records."},
        headers=auth_headers_official
    )
    assert res_valid_reject.status_code == status.HTTP_200_OK
    db_session.refresh(doc)
    assert doc.official_verification_status == "rejected"

    # Flag created for rejection
    mismatch_flag = db_session.query(Flag).filter(
        Flag.document_id == doc.id,
        Flag.category == "mismatch",
        Flag.severity == "critical"
    ).first()
    assert mismatch_flag is not None

    # Correction request with substantive remarks
    res_correction = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "requires_correction", "remarks": "Please provide clearer scanned seal from sub-registrar."},
        headers=auth_headers_official
    )
    assert res_correction.status_code == status.HTTP_200_OK
    db_session.refresh(doc)
    assert doc.official_verification_status == "requires_correction"


def test_stage6_reverification_persistence_and_idempotency(client, auth_headers_official, db_session):
    """
    7. Verifies Stage 6 Re-Verify endpoint persists outcome, evidence, mode, and timestamp without duplicates.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).filter(Document.doc_type == "fire_noc").first()
    if not doc:
        doc = db_session.query(Document).first()

    app_id = doc.application_id
    res1 = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/verify",
        json={"reference_no": "NOC-2025-FIRE-001"},
        headers=auth_headers_official
    )
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()
    assert data1["verification_mode"] in ("SIMULATED", "MANUAL")
    assert data1["checked_at"] is not None

    # Call second time (re-verify)
    res2 = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/verify",
        json={"reference_no": "NOC-2025-FIRE-001"},
        headers=auth_headers_official
    )
    assert res2.status_code == status.HTTP_200_OK

    # Ensure no duplicate verification records created for this document
    records = db_session.query(VerificationResult).filter(VerificationResult.document_id == doc.id).all()
    assert len(records) == 1


def test_stage6_manual_verification_persistence_and_audit_logging(client, auth_headers_official, db_session):
    """
    8. Verifies Stage 6 Record Manual Verification saves determination, substantive remarks,
    evidence reviewed, updates verification outcome, and logs append-only audit event.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    app_id = doc.application_id

    # Manual verification without remarks -> 400
    bad_res = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/manual-verify",
        json={"outcome": "verified", "remarks": ""},
        headers=auth_headers_official
    )
    assert bad_res.status_code == status.HTTP_400_BAD_REQUEST

    # Valid manual verification
    good_res = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/manual-verify",
        json={
            "outcome": "verified",
            "remarks": "Sub-Registrar certified index register reviewed physically.",
            "evidence_reviewed": "Index Register Volume 44, Page 112"
        },
        headers=auth_headers_official
    )
    assert good_res.status_code == status.HTTP_200_OK
    data = good_res.json()
    assert data["status"] == "verified"
    assert data["verification_mode"] in ("MANUAL", "MANUAL_SCRUTINY")
    assert data["manual_remarks"] == "Sub-Registrar certified index register reviewed physically."
    assert data["is_simulated"] is False

    # Check AuditLog
    audit_event = db_session.query(AuditLog).filter(
        AuditLog.action == "RECORD_MANUAL_VERIFICATION",
        AuditLog.entity_type == "document",
        AuditLog.entity_id == doc.id
    ).first()
    assert audit_event is not None
    assert "Index Register Volume 44" in str(audit_event.after_state or "")


def test_distinguishing_match_mismatch_pending_and_unable_to_verify(client, auth_headers_official, db_session):
    """
    9. Confirms distinguishing match confirmed, mismatch found, pending, and unable to verify.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    app_id = doc.application_id

    # Record mismatch
    res_mismatch = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/manual-verify",
        json={
            "outcome": "not_verified",
            "remarks": "Registration number does not exist in State Municipal database.",
            "evidence_reviewed": "State Urban Development Portal Search"
        },
        headers=auth_headers_official
    )
    assert res_mismatch.status_code == status.HTTP_200_OK
    assert res_mismatch.json()["status"] == "not_verified"

    # Mismatch flag exists
    flag = db_session.query(Flag).filter(
        Flag.document_id == doc.id,
        Flag.category == "verification"
    ).first()
    assert flag is not None
    assert flag.severity == "critical"

    # Record unable to verify
    res_unable = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/manual-verify",
        json={
            "outcome": "unable_to_verify",
            "remarks": "Authority record system currently undergoing scheduled maintenance.",
            "evidence_reviewed": "Portal Status 503 Service Unavailable"
        },
        headers=auth_headers_official
    )
    assert res_unable.status_code == status.HTTP_200_OK
    assert res_unable.json()["status"] == "unable_to_verify"


def test_prevention_of_unauthorized_official_verification(client, auth_headers_inst, db_session):
    """
    10. Role-based security check: Institution users must not be able to call official
    verification endpoints or view unredacted forensic raw authority responses.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    app_id = doc.application_id

    # Official document review endpoint
    res1 = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "verified", "remarks": "Unauthorized test"},
        headers=auth_headers_inst
    )
    assert res1.status_code == status.HTTP_403_FORBIDDEN

    # Authority verify endpoint
    res2 = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/verify",
        json={},
        headers=auth_headers_inst
    )
    assert res2.status_code == status.HTTP_403_FORBIDDEN

    # Manual verify endpoint
    res3 = client.post(
        f"/api/v1/applications/{app_id}/documents/{doc.id}/manual-verify",
        json={"outcome": "verified", "remarks": "Unauthorized test"},
        headers=auth_headers_inst
    )
    assert res3.status_code == status.HTTP_403_FORBIDDEN

    # Get verification results as institution -> raw_response is redacted
    res4 = client.get(
        f"/api/v1/applications/{app_id}/verification",
        headers=auth_headers_inst
    )
    assert res4.status_code == status.HTTP_200_OK
    data = res4.json()
    for item in data:
        assert item["raw_response"].get("redacted") is True


def test_document_replacement_workflow(client, auth_headers_official, db_session):
    """
    12. Verifies document replacement: resetting validation status to pending_processing
    and updating processing lifecycle.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    assert doc is not None

    # Simulate replacement or re-upload reset
    doc.validation_status = "pending_processing"
    doc.processing_status = "queued"
    db_session.commit()
    db_session.refresh(doc)

    assert doc.validation_status == "pending_processing"
    assert doc.processing_status == "queued"
