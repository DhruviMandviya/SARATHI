import os
import pytest
from pathlib import Path
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.scripts.seed_sample_scenarios import seed_sample_scenarios

def test_authorized_pdf_preview(client, official_token, institution_token, db_session):
    """Verifies that an authorized user receives inline PDF bytes and page render image."""
    seed_sample_scenarios(db=db_session)
    pdf_doc = db_session.query(Document).filter(
        Document.mime_type == "application/pdf",
        Document.application.has(institution_id=1)
    ).first()
    assert pdf_doc is not None

    # Test /file endpoint
    res_file = client.get(f"/api/v1/documents/{pdf_doc.id}/file?token={institution_token}")
    assert res_file.status_code == 200
    assert "application/pdf" in res_file.headers.get("content-type", "")
    assert "inline" in res_file.headers.get("content-disposition", "")
    assert res_file.headers.get("accept-ranges") == "bytes"
    assert len(res_file.content) > 0

    # Test /page/1/image endpoint
    res_page = client.get(f"/api/v1/documents/{pdf_doc.id}/page/1/image?token={institution_token}")
    assert res_page.status_code == 200
    assert "image/png" in res_page.headers.get("content-type", "")
    assert "inline" in res_page.headers.get("content-disposition", "")
    assert len(res_page.content) > 0

def test_authorized_png_preview(client, official_token, institution_token, db_session):
    """Verifies that an authorized user can preview image documents directly and as page images."""
    seed_sample_scenarios(db=db_session)
    img_doc = db_session.query(Document).filter(
        Document.mime_type.like("%image%"),
        Document.application.has(institution_id=1)
    ).first()
    assert img_doc is not None

    # Test /file endpoint
    res_file = client.get(f"/api/v1/documents/{img_doc.id}/file?token={institution_token}")
    assert res_file.status_code == 200
    assert "image" in res_file.headers.get("content-type", "")
    assert "inline" in res_file.headers.get("content-disposition", "")

    # Test /page/1/image endpoint
    res_page = client.get(f"/api/v1/documents/{img_doc.id}/page/1/image?token={institution_token}")
    assert res_page.status_code == 200
    assert "image/png" in res_page.headers.get("content-type", "")
    assert "inline" in res_page.headers.get("content-disposition", "")

def test_missing_file_handling(client, official_token, db_session):
    """Verifies that a document with missing file on disk returns 404."""
    seed_sample_scenarios(db=db_session)
    dummy_doc = Document(
        application_id=1,
        doc_type="affidavit",
        original_filename="missing_test_file.pdf",
        stored_path="nonexistent_folder/missing_file_xyz.pdf",
        mime_type="application/pdf",
        size=1024,
        processing_status="queued",
        validation_status="valid"
    )
    db_session.add(dummy_doc)
    db_session.commit()
    db_session.refresh(dummy_doc)

    try:
        res_file = client.get(f"/api/v1/documents/{dummy_doc.id}/file?token={official_token}")
        assert res_file.status_code == 404

        res_page = client.get(f"/api/v1/documents/{dummy_doc.id}/page/1/image?token={official_token}")
        assert res_page.status_code == 404
    finally:
        db_session.delete(dummy_doc)
        db_session.commit()

def test_invalid_and_expired_authentication(client, db_session):
    """Verifies that requests without credentials or with invalid tokens are rejected with 401."""
    seed_sample_scenarios(db=db_session)
    pdf_doc = db_session.query(Document).first()
    assert pdf_doc is not None

    # No token
    res1 = client.get(f"/api/v1/documents/{pdf_doc.id}/file")
    assert res1.status_code == 401

    res2 = client.get(f"/api/v1/documents/{pdf_doc.id}/page/1/image")
    assert res2.status_code == 401

    # Invalid token
    res3 = client.get(f"/api/v1/documents/{pdf_doc.id}/file?token=invalid.token.payload")
    assert res3.status_code == 401

def test_unauthorized_access_to_another_institution_document(client, db_session):
    """Verifies that institution 2 cannot access institution 1's document file or page image."""
    seed_sample_scenarios(db=db_session)
    # Login as inst2
    res_login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "inst2@aicte.gov.in", "password": "Demo@Password123"}
    )
    inst2_token = res_login2.json()["access_token"]

    doc_inst1 = db_session.query(Document).filter(
        Document.application.has(institution_id=1)
    ).first()
    assert doc_inst1 is not None

    # Institution 2 attempt
    res_file = client.get(f"/api/v1/documents/{doc_inst1.id}/file?token={inst2_token}")
    assert res_file.status_code == 403
    assert "access denied" in res_file.json().get("detail", "").lower()

    res_page = client.get(f"/api/v1/documents/{doc_inst1.id}/page/1/image?token={inst2_token}")
    assert res_page.status_code == 403

def test_preview_when_ocr_pending_or_failed(client, institution_token, db_session):
    """Verifies preview works even when document processing status is queued or failed."""
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).filter(
        Document.application.has(institution_id=1),
        Document.mime_type == "application/pdf"
    ).first()
    assert doc is not None

    orig_status = doc.processing_status
    doc.processing_status = "failed"
    doc.processing_error = "Synthetic simulated OCR timeout"
    db_session.commit()

    try:
        # File still serves 200
        res_file = client.get(f"/api/v1/documents/{doc.id}/file?token={institution_token}")
        assert res_file.status_code == 200

        # Page still renders 200
        res_page = client.get(f"/api/v1/documents/{doc.id}/page/1/image?token={institution_token}")
        assert res_page.status_code == 200
    finally:
        doc.processing_status = orig_status
        doc.processing_error = None
        db_session.commit()

def test_backend_authorization_for_internal_endpoints(client, institution_token, db_session):
    """Verifies that institution users cannot access official scrutiny, decision, or audit endpoints."""
    seed_sample_scenarios(db=db_session)

    # Official Decision endpoint
    res_dec = client.post(
        "/api/v1/applications/1/decision",
        json={"outcome": "approved", "remarks": "Unauthorized attempt"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_dec.status_code == 403

    # Audit Trail
    res_audit = client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_audit.status_code == 403

    # Update Deficiency Letter
    res_def = client.post(
        "/api/v1/applications/1/deficiency-letter",
        json={"letter_text": "Unauthorized notice"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_def.status_code == 403

    # External Authenticity Verification Trigger
    res_ver = client.post(
        "/api/v1/applications/1/documents/1/verify",
        json={"reference_no": "TEST-123"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_ver.status_code == 403

    # Force compliance re-evaluation
    res_comp = client.get(
        "/api/v1/applications/1/compliance?re_evaluate=true",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_comp.status_code == 403

def test_institution_cannot_modify_submitted_application(client, institution_token, db_session):
    """Verifies that an institution cannot modify declared details on non-draft applications."""
    seed_sample_scenarios(db=db_session)
    app_submitted = db_session.query(Application).filter(
        Application.institution_id == 1,
        Application.status.in_(["submitted", "under_verification", "needs_review"])
    ).first()
    assert app_submitted is not None

    res = client.put(
        f"/api/v1/applications/{app_submitted.id}/declared-details",
        json={"institution_name": "Tampered Name Attempt"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res.status_code == 400
    assert "cannot be modified" in res.json().get("detail", "").lower()

def test_applicant_dashboard_summary_scoped(client, institution_token, db_session):
    """Verifies that dashboard summary returns draft and submitted metrics scoped to the caller."""
    seed_sample_scenarios(db=db_session)
    res_inst = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res_inst.status_code == 200
    data = res_inst.json()
    assert "total_applications" in data
    assert "draft" in data
    assert "submitted" in data
    assert "status_distribution" in data

def test_synthetic_generator_idempotency(db_session):
    """Verifies that calling seed_sample_scenarios repeatedly is completely idempotent."""
    seed_sample_scenarios(db=db_session)
    count_apps_1 = db_session.query(Application).count()
    count_docs_1 = db_session.query(Document).count()

    # Re-run generator
    seed_sample_scenarios(db=db_session)
    count_apps_2 = db_session.query(Application).count()
    count_docs_2 = db_session.query(Document).count()

    assert count_apps_1 == count_apps_2
    assert count_docs_1 == count_docs_2

def test_account_switching_and_isolation(client, db_session):
    """Verifies that switching accounts isolates application data and blocks cross-tenant access."""
    seed_sample_scenarios(db=db_session)

    # Login as Institution 1
    res1 = client.post("/api/v1/auth/login", data={"username": "inst1@aicte.gov.in", "password": "Demo@Password123"})
    assert res1.status_code == 200
    token1 = res1.json()["access_token"]

    # Login as Institution 2
    res2 = client.post("/api/v1/auth/login", data={"username": "inst2@aicte.gov.in", "password": "Demo@Password123"})
    assert res2.status_code == 200
    token2 = res2.json()["access_token"]

    # Institution 1 lists their applications
    res_list1 = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token1}"})
    assert res_list1.status_code == 200
    apps1 = res_list1.json()
    assert len(apps1) > 0
    app1_id = apps1[0]["id"]

    # Institution 2 lists their applications (must not contain app1_id)
    res_list2 = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token2}"})
    assert res_list2.status_code == 200
    apps2 = res_list2.json()
    assert all(a["id"] != app1_id for a in apps2)

    # Institution 2 directly attempts to open Institution 1's application -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/applications/{app1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res_forbidden.status_code == 403

