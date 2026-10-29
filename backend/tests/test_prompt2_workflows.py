import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.models.application import Application
from backend.app.models.decision import Decision, DeficiencyLetter
from backend.app.models.information_request import InformationRequest, InformationResponse
from backend.app.services.notice_sync import persist_official_notice_for_application, sync_unpersisted_info_requested_notices
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

def test_issued_notice_persists_and_appears_in_information_requests(client, db_session, auth_headers_inst1, auth_headers_official):
    """
    Verifies that when an official issues an 'info_requested' decision:
    1. A formal InformationRequest is persisted with reference_no ending in DEF-01.
    2. It appears in GET /api/v1/information-requests for the institution.
    3. The application status transitions to info_requested.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # Official commits decision
    res = client.post(
        f"/api/v1/applications/{app.id}/decision",
        headers=auth_headers_official,
        json={
            "outcome": "info_requested",
            "remarks": "Mandatory title deed survey numbers and certified land area schedule missing."
        }
    )
    assert res.status_code == status.HTTP_200_OK

    # Check that InformationRequest was persisted
    req = db_session.query(InformationRequest).filter(
        InformationRequest.application_id == app.id
    ).order_by(InformationRequest.id.desc()).first()
    assert req is not None
    assert "DEF-01" in req.reference_no
    assert req.status == "action_required"
    assert req.institution_id == 1
    assert len(req.deficiencies) > 0

    # Institution retrieves information requests list
    list_res = client.get("/api/v1/information-requests", headers=auth_headers_inst1)
    assert list_res.status_code == status.HTTP_200_OK
    data = list_res.json()
    refs = [item["reference_no"] for item in data]
    assert req.reference_no in refs

    # Summary cards check
    sum_res = client.get("/api/v1/information-requests/summary-cards", headers=auth_headers_inst1)
    assert sum_res.status_code == status.HTTP_200_OK
    sum_data = sum_res.json()
    assert sum_data["action_required"] >= 1

def test_draft_or_unissued_notice_is_hidden_from_applicant(client, db_session, auth_headers_inst1, auth_headers_official):
    """
    A draft deficiency letter or unissued notice must NEVER be exposed as an official instruction to the applicant.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1, Application.status == "draft").first()
    if not app:
        app = Application(
            application_no="APP-TEST-DRAFT-01",
            institution_id=1,
            type="New Technical Institution",
            academic_year="2026-2027",
            status="draft",
            risk_score=0.0,
            risk_band="Low",
            declared_details={"institution_name": "Apex Test Campus"}
        )
        db_session.add(app)
        db_session.commit()
        db_session.refresh(app)

    # Official saves draft deficiency letter
    save_res = client.post(
        f"/api/v1/applications/{app.id}/deficiency-letter",
        headers=auth_headers_official,
        json={"letter_text": "Draft notice text: This is an internal official draft."}
    )
    assert save_res.status_code == status.HTTP_200_OK

    # Applicant queries deficiency letter
    app_res = client.get(
        f"/api/v1/applications/{app.id}/deficiency-letter",
        headers=auth_headers_inst1
    )
    # Must return 404 because notice was NOT formally issued
    assert app_res.status_code == status.HTTP_404_NOT_FOUND
    assert "No official deficiency notice has been issued" in app_res.json()["detail"]

def test_tenant_isolation_information_requests(client, db_session, auth_headers_inst1, auth_headers_inst2, auth_headers_official):
    """
    Strict tenant isolation: Institution 2 must never access notices belonging to Institution 1.
    """
    seed_sample_scenarios(db=db_session)
    app1 = db_session.query(Application).filter(Application.institution_id == 1).first()

    # Issue notice for Institution 1
    client.post(
        f"/api/v1/applications/{app1.id}/decision",
        headers=auth_headers_official,
        json={
            "outcome": "info_requested",
            "remarks": "Rectify institutional trust deed discrepancies."
        }
    )

    req1 = db_session.query(InformationRequest).filter(InformationRequest.application_id == app1.id).first()
    assert req1 is not None

    # Institution 2 lists requests: must NOT include req1
    list_res = client.get("/api/v1/information-requests", headers=auth_headers_inst2)
    assert list_res.status_code == status.HTTP_200_OK
    inst2_refs = [r["reference_no"] for r in list_res.json()]
    assert req1.reference_no not in inst2_refs

    # Institution 2 direct access to req1: must return 403 Forbidden
    detail_res = client.get(f"/api/v1/information-requests/{req1.id}", headers=auth_headers_inst2)
    assert detail_res.status_code == status.HTTP_403_FORBIDDEN

def test_applicant_response_save_draft_and_submit(client, db_session, auth_headers_inst1, auth_headers_official):
    """
    Applicant can save response drafts and submit formal responses with validation.
    Submitting does NOT automatically resolve the request (official review required).
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()

    client.post(
        f"/api/v1/applications/{app.id}/decision",
        headers=auth_headers_official,
        json={
            "outcome": "info_requested",
            "remarks": "Submit missing municipal building sanction certificate."
        }
    )

    req = db_session.query(InformationRequest).filter(
        InformationRequest.application_id == app.id
    ).order_by(InformationRequest.id.desc()).first()
    assert req is not None

    def_id = req.deficiencies[0]["id"]

    # 1. Save draft response
    draft_res = client.post(
        f"/api/v1/information-requests/{req.id}/response/draft",
        headers=auth_headers_inst1,
        json={
            "items": [
                {
                    "deficiency_id": def_id,
                    "explanation": "We have applied to the municipal corporation and are awaiting stamp.",
                    "status": "draft"
                }
            ]
        }
    )
    assert draft_res.status_code == status.HTTP_200_OK
    draft_data = draft_res.json()
    assert draft_data["status"] == "draft"

    # Verify request status remains action_required
    db_session.refresh(req)
    assert req.status == "action_required"

    # 2. Upload valid PDF for the deficiency slot
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sanctioned Building Plan Municipal Approval")
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        f"/api/v1/information-requests/{req.id}/upload-deficiency-doc",
        headers=auth_headers_inst1,
        files={"file": ("sanctioned_plan.pdf", pdf_bytes, "application/pdf")},
        data={"deficiency_id": def_id, "doc_type": "building_plan"}
    )
    assert upload_res.status_code == status.HTTP_200_OK
    doc_id = upload_res.json()["document_id"]

    # 3. Submit formal response
    submit_items = []
    for d in req.deficiencies:
        submit_items.append({
            "deficiency_id": d["id"],
            "explanation": "Certified municipal sanction and statutory compliance submitted.",
            "document_id": doc_id,
            "original_filename": "sanctioned_plan.pdf",
            "status": "completed"
        })

    submit_res = client.post(
        f"/api/v1/information-requests/{req.id}/response/submit",
        headers=auth_headers_inst1,
        json={"items": submit_items}
    )
    assert submit_res.status_code == status.HTTP_200_OK
    submit_data = submit_res.json()
    assert submit_data["status"] == "submitted"
    assert submit_data["submission_receipt"] is not None
    assert "RCP-2026-" in submit_data["submission_receipt"]

    # 4. Request status is now 'submitted' (NOT automatically resolved)
    db_session.refresh(req)
    assert req.status == "submitted"
    db_session.refresh(app)
    assert app.status == "needs_review"

    # 5. Official reviews and resolves the request
    review_res = client.post(
        f"/api/v1/information-requests/{req.id}/review",
        headers=auth_headers_official,
        json={
            "outcome": "resolved",
            "notes": "Verified municipal building approval certificate complies with APH Norms."
        }
    )
    assert review_res.status_code == status.HTTP_200_OK

    db_session.refresh(req)
    assert req.status == "resolved"
    db_session.refresh(app)
    assert app.status == "under_verification"

def test_applicant_reports_and_decisions_redacted(client, db_session, auth_headers_inst1, auth_headers_official):
    """
    Applicant Reports view redacts internal scores, risk bands, and top contributing factors.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()

    # Official query gets full report
    off_res = client.get(f"/api/v1/applications/{app.id}/report", headers=auth_headers_official)
    assert off_res.status_code == status.HTTP_200_OK
    off_data = off_res.json()
    assert "risk_score" in off_data

    # Applicant query gets redacted report
    app_res = client.get(f"/api/v1/applications/{app.id}/report", headers=auth_headers_inst1)
    assert app_res.status_code == status.HTTP_200_OK
    app_data = app_res.json()
    assert app_data["risk_score"] == 0.0
    assert app_data["risk_band"] == ""
    assert app_data["risk_breakdown"] == {}
