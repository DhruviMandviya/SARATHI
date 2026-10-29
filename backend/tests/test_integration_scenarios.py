import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.finding import Flag
from backend.app.models.verification import VerificationResult
from backend.scripts.seed_sample_scenarios import seed_sample_scenarios

def test_seeded_scenarios_and_documents(db_session):
    """Verify that synthetic scenarios are seeded with correct relationships."""
    seed_sample_scenarios(db=db_session)

    apps = db_session.query(Application).filter(Application.application_no.like("APP-2025-SCEN-%")).all()
    assert len(apps) >= 10, f"Expected at least 10 seeded scenario applications, got {len(apps)}"

    # Scenario A: Pristine has 5 documents
    app_a = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-A").first()
    assert app_a is not None
    docs_a = db_session.query(Document).filter(Document.application_id == app_a.id).all()
    doc_types_a = {d.doc_type for d in docs_a}
    assert {"land_document", "building_plan", "fire_noc", "society_registration", "affidavit"}.issubset(doc_types_a)

    # Scenario B: Missing Fire NOC (deliberately omitted)
    app_b = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-B").first()
    assert app_b is not None
    docs_b = db_session.query(Document).filter(Document.application_id == app_b.id).all()
    doc_types_b = {d.doc_type for d in docs_b}
    assert "fire_noc" not in doc_types_b, "Scenario B must deliberately omit fire_noc"
    assert "land_document" in doc_types_b
    assert "building_plan" in doc_types_b

def test_document_detailed_endpoint(client, official_token, db_session):
    """Test /applications/{application_id}/documents-detailed returns full document list with fields."""
    seed_sample_scenarios(db=db_session)
    app_a = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-A").first()
    assert app_a is not None

    res = client.get(
        f"/api/v1/applications/{app_a.id}/documents-detailed",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) == 5
    for doc in docs:
        assert "doc_type" in doc
        assert "extracted_fields" in doc

def test_document_file_retrieval(client, official_token, db_session):
    """Test /documents/{id}/file resolves stored path and serves file."""
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).first()
    assert doc is not None

    # Verify file exists on disk
    assert Path(doc.stored_path).exists(), f"Stored path does not exist: {doc.stored_path}"

    res = client.get(
        f"/api/v1/documents/{doc.id}/file",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert res.status_code == 200
    assert len(res.content) > 0

def test_simulated_authenticity_checks(db_session):
    """Test all verification results are explicitly marked as is_simulated=True."""
    seed_sample_scenarios(db=db_session)
    results = db_session.query(VerificationResult).all()
    assert len(results) > 0, "Expected verification results to be present"
    for vr in results:
        assert vr.is_simulated is True, f"VerificationResult ID {vr.id} is not marked as simulated"

def test_cross_institution_unauthorized_access(client, institution_token, db_session):
    """Test institution 1 cannot access institution 2 applications."""
    seed_sample_scenarios(db=db_session)
    # Scenario B belongs to Zenith (institution 2)
    app_b = db_session.query(Application).filter(Application.application_no == "APP-2025-SCEN-B").first()
    assert app_b is not None

    # Institution 1 attempts to access Institution 2 application
    res = client.get(
        f"/api/v1/applications/{app_b.id}",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res.status_code == 403

def test_cors_preflight_ports(client):
    """Test CORS preflight allows both port 3000 and 3001 origins."""
    for origin in ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3001", "http://127.0.0.1:3000"]:
        res = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
