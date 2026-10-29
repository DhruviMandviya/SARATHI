import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.models.application import Application
from backend.app.models.decision import Decision
from backend.app.models.information_request import InformationRequest
from backend.scripts.seed_sample_scenarios import seed_sample_scenarios

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers_inst1():
    token = create_access_token(subject=1, role="institution", institution_id=1)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_inst2():
    token = create_access_token(subject=2, role="institution", institution_id=2)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_official():
    token = create_access_token(subject=3, role="official", institution_id=None)
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# 1. Authentication and Two Demo Personas
# ============================================================================

def test_two_demo_personas_authentication(client, db_session):
    """
    Verifies that the two primary demo personas authenticate correctly through /auth/login:
    1. AICTE Official: official@aicte.gov.in
    2. Institution Applicant: inst1@aicte.gov.in
    And invalid credentials are systematically rejected.
    """
    seed_sample_scenarios(db=db_session)

    # 1. Official demo login
    off_res = client.post("/api/v1/auth/login", json={
        "email": "official@aicte.gov.in",
        "password": "Demo@Password123"
    })
    assert off_res.status_code == status.HTTP_200_OK
    off_data = off_res.json()
    assert off_data["role"] in ("official", "admin")
    assert "access_token" in off_data

    # 2. Institution Applicant demo login
    inst_res = client.post("/api/v1/auth/login", json={
        "email": "inst1@aicte.gov.in",
        "password": "Demo@Password123"
    })
    assert inst_res.status_code == status.HTTP_200_OK
    inst_data = inst_res.json()
    assert inst_data["role"] == "institution"
    assert inst_data["institution_id"] == 1
    assert "access_token" in inst_data

    # 3. Invalid credentials rejected
    bad_res = client.post("/api/v1/auth/login", json={
        "email": "official@aicte.gov.in",
        "password": "WrongPassword999!"
    })
    assert bad_res.status_code == status.HTTP_401_UNAUTHORIZED

# ============================================================================
# 2. Frontend-Backend Connectivity & Health Check
# ============================================================================

def test_connectivity_and_health_endpoints(client):
    """
    Verifies that health check endpoints return healthy status, service name,
    and api_docs matching the specification.
    """
    for endpoint in ["/", "/health", "/api/v1/health"]:
        res = client.get(endpoint)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "healthy"
        assert "AICTE" in data["service"]
        assert data["api_docs"] == "/api/v1/docs"

# ============================================================================
# 3. New Application Form and Declared Parameters Validation
# ============================================================================

def test_declared_details_validation_flow(client, auth_headers_inst1):
    """
    Verifies mandatory declared details validation pre-check:
    - Returns is_valid=True and valid=True when all parameters are valid
    - Returns is_valid=False and valid=False with specific field error keys when invalid
    """
    # 1. Missing mandatory fields
    incomplete = {
        "institution_name": "",
        "land_area_acres": -2.5,
        "built_up_area_sqm": 0,
        "student_intake": 0
    }
    res_bad = client.post(
        "/api/v1/applications/validate-declared-details",
        headers=auth_headers_inst1,
        json=incomplete
    )
    assert res_bad.status_code == status.HTTP_200_OK
    bad_data = res_bad.json()
    assert bad_data["is_valid"] is False
    assert bad_data["valid"] is False
    assert "institution_name" in bad_data["errors"]
    assert "trust_name" in bad_data["errors"]
    assert "land_area_acres" in bad_data["errors"]
    assert "built_up_area_sqm" in bad_data["errors"]
    assert "student_intake" in bad_data["errors"]

    # 2. Valid complete declared parameters
    valid_data = {
        "institution_name": "Apex Institute of Advanced Technology",
        "trust_name": "Apex Education Trust",
        "address": "Sector 14, Plot 8, Kharghar, Navi Mumbai",
        "state": "Maharashtra",
        "land_area_acres": 3.25,
        "built_up_area_sqm": 4500.0,
        "student_intake": 300,
        "faculty_count": 20,
        "student_faculty_ratio": 15.0,
        "labs_count": 12,
        "ews_quota_percentage": 10.0,
        "corpus_fund_lakhs": 150.0,
        "affidavit_stamp_value_inr": 100.0
    }
    res_ok = client.post(
        "/api/v1/applications/validate-declared-details",
        headers=auth_headers_inst1,
        json=valid_data
    )
    assert res_ok.status_code == status.HTTP_200_OK
    ok_data = res_ok.json()
    assert ok_data["is_valid"] is True
    assert ok_data["valid"] is True
    assert len(ok_data["errors"]) == 0

# ============================================================================
# 4. Official Application Queue Draft Filtering
# ============================================================================

def test_official_queue_excludes_drafts_by_default(client, auth_headers_official, auth_headers_inst1, db_session):
    """
    Verifies that the official active scrutiny queue excludes draft applications
    by default, while allowing drafts to be viewed if status=draft is explicitly requested.
    """
    seed_sample_scenarios(db=db_session)

    # Create an unsubmitted draft
    draft_res = client.post(
        "/api/v1/applications",
        headers=auth_headers_inst1,
        json={
            "type": "New Technical Institution",
            "academic_year": "2026-2027",
            "declared_details": {
                "institution_name": "Testing Unsubmitted Draft",
                "land_area_acres": 3.0
            }
        }
    )
    assert draft_res.status_code == status.HTTP_200_OK
    draft_id = draft_res.json()["id"]

    # Official queries default queue (no status filter)
    queue_res = client.get("/api/v1/applications", headers=auth_headers_official)
    assert queue_res.status_code == status.HTTP_200_OK
    default_apps = queue_res.json()
    # Ensure draft application is NOT in default active scrutiny queue
    default_ids = [a["id"] for a in default_apps]
    assert draft_id not in default_ids
    for a in default_apps:
        assert a["status"] != "draft"

    # Official queries drafts specifically
    draft_queue_res = client.get("/api/v1/applications?status=draft", headers=auth_headers_official)
    assert draft_queue_res.status_code == status.HTTP_200_OK
    draft_apps = draft_queue_res.json()
    draft_ids = [a["id"] for a in draft_apps]
    assert draft_id in draft_ids

# ============================================================================
# 5. Stage 9 Official Decision Rationale & Placeholder Validation
# ============================================================================

def test_official_decision_requires_meaningful_remarks(client, auth_headers_official, db_session):
    """
    Verifies that committing a binding decision requires non-empty, substantive
    remarks (rejects empty or trivial remarks).
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # Attempt to commit decision with empty remarks
    res_empty = client.post(
        f"/api/v1/applications/{app.id}/decision",
        headers=auth_headers_official,
        json={"outcome": "approved", "remarks": "   "}
    )
    assert res_empty.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)
