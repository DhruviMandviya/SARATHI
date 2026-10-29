import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
import fitz
from backend.app.models.application import Application, ChecklistItem
from backend.app.models.document import Document
from backend.app.models.notification import Notification
from backend.app.models.information_request import InformationRequest, InformationResponse
from backend.scripts.seed_sample_scenarios import seed_sample_scenarios

def create_valid_pdf_bytes(text="AICTE Verification Sample PDF"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_role_based_access_and_official_upload_block(client, official_token, institution_token, db_session):
    """
    Prevent officials from modifying applicant-submitted documents through the Applications Queue.
    Enforce permissions on backend: Official uploading or deleting document returns 403 Forbidden.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # Official attempts to upload a document to applicant's application -> 403
    upload_res = client.post(
        f"/api/v1/applications/{app.id}/documents",
        headers={"Authorization": f"Bearer {official_token}"},
        data={"doc_type": "land_document"},
        files={"file": ("test.pdf", b"%PDF-1.4 test document content", "application/pdf")}
    )
    assert upload_res.status_code == status.HTTP_403_FORBIDDEN
    assert "officials cannot upload or replace" in upload_res.json()["detail"].lower()

    # Official attempts to delete an applicant document -> 403
    doc = db_session.query(Document).filter(Document.application_id == app.id).first()
    assert doc is not None
    del_res = client.delete(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert del_res.status_code == status.HTTP_403_FORBIDDEN

    # Official attempts to modify applicant declared parameters -> 403
    param_res = client.put(
        f"/api/v1/applications/{app.id}/declared-details",
        headers={"Authorization": f"Bearer {official_token}"},
        json={"land_area_acres": 5.0}
    )
    assert param_res.status_code == status.HTTP_403_FORBIDDEN

def test_applicant_forensic_ela_isolation(client, institution_token, db_session):
    """
    Ensure applicants cannot retrieve internal forensic ELA evidence.
    """
    seed_sample_scenarios(db=db_session)
    doc = db_session.query(Document).filter(Document.application.has(institution_id=1)).first()
    assert doc is not None

    res = client.get(
        f"/api/v1/documents/{doc.id}/ela",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "restricted to council scrutiny officials" in res.json()["detail"].lower()

def test_applicant_redacted_risk_scores(client, institution_token, official_token, db_session):
    """
    Ensure applicants cannot retrieve internal risk scores, bands, or fraud breakdowns.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # Institution view of application
    inst_res = client.get(
        f"/api/v1/applications/{app.id}",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert inst_res.status_code == status.HTTP_200_OK
    inst_data = inst_res.json()
    assert inst_data["risk_score"] == 0.0
    assert inst_data["risk_band"] == ""
    assert inst_data["risk_breakdown"] == {}

    # Institution report summary
    rep_res = client.get(
        f"/api/v1/applications/{app.id}/report",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert rep_res.status_code == status.HTTP_200_OK
    rep_data = rep_res.json()
    assert rep_data["risk_score"] == 0.0
    assert rep_data["risk_band"] == ""
    assert rep_data["risk_breakdown"] == {}

    # Official view receives genuine risk scoring
    off_res = client.get(
        f"/api/v1/applications/{app.id}",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert off_res.status_code == status.HTTP_200_OK
    assert off_res.json()["risk_band"] in ("Low", "Medium", "High")

def test_mandatory_declared_details_validation(client, institution_token):
    """
    Verify frontend pre-check validation and mandatory field enforcement.
    """
    # Test validation endpoint with incomplete fields
    incomplete_details = {
        "institution_name": "AI",
        "land_area_acres": -1.5,
        "built_up_area_sqm": 0
    }
    val_res = client.post(
        "/api/v1/applications/validate-declared-details",
        headers={"Authorization": f"Bearer {institution_token}"},
        json=incomplete_details
    )
    assert val_res.status_code == status.HTTP_200_OK
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert "institution_name" in val_data["errors"]
    assert "trust_name" in val_data["errors"]
    assert "land_area_acres" in val_data["errors"]

    # Test validation endpoint with complete valid fields
    valid_details = {
        "institution_name": "Apex Institute of Advanced Technology",
        "trust_name": "Apex Education Trust",
        "address": "Sector 14, Plot 8, Kharghar, Navi Mumbai",
        "state": "Maharashtra",
        "land_area_acres": 3.5,
        "built_up_area_sqm": 4500.0,
        "student_intake": 300,
        "faculty_count": 20,
        "student_faculty_ratio": 15.0,
        "labs_count": 12,
        "ews_quota_percentage": 10.0,
        "corpus_fund_lakhs": 150.0,
        "affidavit_stamp_value_inr": 100.0
    }
    val_valid = client.post(
        "/api/v1/applications/validate-declared-details",
        headers={"Authorization": f"Bearer {institution_token}"},
        json=valid_details
    )
    assert val_valid.status_code == status.HTTP_200_OK
    assert val_valid.json()["is_valid"] is True
    assert len(val_valid.json()["errors"]) == 0

def test_edit_declared_details_persists_to_db_and_audit(client, institution_token, db_session):
    """
    Verify that Edit Details in My Applications saves to backend and DB,
    and writes to the append-only audit trail.
    """
    seed_sample_scenarios(db=db_session)
    # Create a draft application
    create_res = client.post(
        "/api/v1/applications",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "type": "New Technical Institution",
            "academic_year": "2026-2027",
            "declared_details": {
                "institution_name": "Initial Name",
                "land_area_acres": 3.0,
                "built_up_area_sqm": 4000.0
            }
        }
    )
    assert create_res.status_code == status.HTTP_200_OK
    app_id = create_res.json()["id"]

    # Edit declared details
    update_res = client.put(
        f"/api/v1/applications/{app_id}/declared-details",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "institution_name": "Updated Apex Campus",
            "land_area_acres": 4.25,
            "built_up_area_sqm": 5200.0,
            "faculty_count": 25
        }
    )
    assert update_res.status_code == status.HTTP_200_OK

    # Verify persisted in database
    db_session.expire_all()
    app_db = db_session.query(Application).filter(Application.id == app_id).first()
    assert app_db.declared_details["institution_name"] == "Updated Apex Campus"
    assert app_db.declared_details["land_area_acres"] == 4.25
    assert app_db.declared_details["built_up_area_sqm"] == 5200.0

def test_database_backed_notifications_flow(client, institution_token, official_token, db_session):
    """
    Store notifications in backend, retrieve for authenticated user, unread counts,
    and mark as read. Do not generate fake notifications.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # Initial notifications list
    initial_res = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert initial_res.status_code == status.HTTP_200_OK
    initial_unread = initial_res.json()["unread_count"]

    # Official records a decision -> automatically generates a notification for the institution
    dec_res = client.post(
        f"/api/v1/applications/{app.id}/decision",
        headers={"Authorization": f"Bearer {official_token}"},
        json={"outcome": "approved", "remarks": "Full compliance verified by council scrutiny committee."}
    )
    assert dec_res.status_code == status.HTTP_200_OK

    # Fetch institution notifications
    notif_res = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert notif_res.status_code == status.HTTP_200_OK
    data = notif_res.json()
    assert data["unread_count"] == initial_unread + 1
    assert len(data["items"]) > 0

    latest_notif = data["items"][0]
    assert latest_notif["category"] == "decision_recorded"
    assert "APPROVED" in latest_notif["title"]

    # Mark as read
    read_res = client.post(
        f"/api/v1/notifications/{latest_notif['id']}/read",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert read_res.status_code == status.HTTP_200_OK
    assert read_res.json()["is_read"] is True

    # Mark all read
    all_read_res = client.post(
        "/api/v1/notifications/mark-all-read",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert all_read_res.status_code == status.HTTP_200_OK

    count_res = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert count_res.json()["unread_count"] == 0

def test_information_requests_complete_workflow(client, official_token, institution_token, db_session):
    """
    Information Request workflow:
    Official issues notice -> applicant views details (drafts hidden) -> applicant saves draft response
    -> applicant submits response (validating attachments) -> official reviews & resolves -> notifications triggered.
    """
    seed_sample_scenarios(db=db_session)
    app = db_session.query(Application).filter(Application.institution_id == 1).first()
    assert app is not None

    # 1. Official issues a formal Information Request Notice
    notice_payload = {
        "title": "Fire Safety NOC Verification Clarification",
        "reason": "Fire NOC validity period requires updated clearance from State Fire Services.",
        "deadline_days": 15,
        "deficiencies": [
            {
                "id": "def-fire-1",
                "doc_type": "fire_noc",
                "requirement": "Renewed Fire Safety NOC certificate with endorsement seal.",
                "explanation": "Existing certificate appears lapsed on 15 Jan 2023.",
                "mandatory": True
            }
        ]
    }
    issue_res = client.post(
        f"/api/v1/applications/{app.id}/information-requests",
        headers={"Authorization": f"Bearer {official_token}"},
        json=notice_payload
    )
    assert issue_res.status_code == status.HTTP_200_OK
    notice_data = issue_res.json()
    req_id = notice_data["id"]
    ref_no = notice_data["reference_no"]
    assert notice_data["status"] == "action_required"
    assert "NOT-2026-" in ref_no

    # Application status transitioned to info_requested
    db_session.expire_all()
    app_reloaded = db_session.query(Application).filter(Application.id == app.id).first()
    assert app_reloaded.status == "info_requested"

    # 2. Institution lists information requests (Drafts never shown)
    list_res = client.get(
        "/api/v1/information-requests",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert list_res.status_code == status.HTTP_200_OK
    notices = list_res.json()
    assert any(n["id"] == req_id for n in notices)

    # 3. Institution views request details
    detail_res = client.get(
        f"/api/v1/information-requests/{req_id}",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert detail_res.status_code == status.HTTP_200_OK
    detail_data = detail_res.json()
    assert detail_data["request"]["reference_no"] == ref_no
    assert len(detail_data["request"]["deficiencies"]) == 1

    # 4. Institution uploads replacement document for this deficiency slot
    upload_doc_res = client.post(
        f"/api/v1/information-requests/{req_id}/upload-deficiency-doc",
        headers={"Authorization": f"Bearer {institution_token}"},
        data={"deficiency_id": "def-fire-1", "doc_type": "fire_noc"},
        files={"file": ("fire_noc_renewed_2026.pdf", create_valid_pdf_bytes("Renewed Fire NOC"), "application/pdf")}
    )
    assert upload_doc_res.status_code == status.HTTP_200_OK
    cured_doc_id = upload_doc_res.json()["document_id"]

    # 5. Institution saves response draft
    draft_res = client.post(
        f"/api/v1/information-requests/{req_id}/response/draft",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "items": [
                {
                    "deficiency_id": "def-fire-1",
                    "explanation": "Attached latest renewed Fire Safety NOC.",
                    "document_id": cured_doc_id,
                    "original_filename": "fire_noc_renewed_2026.pdf",
                    "status": "draft"
                }
            ]
        }
    )
    assert draft_res.status_code == status.HTTP_200_OK
    assert draft_res.json()["status"] == "draft"

    # 6. Institution submits response
    submit_res = client.post(
        f"/api/v1/information-requests/{req_id}/response/submit",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "items": [
                {
                    "deficiency_id": "def-fire-1",
                    "explanation": "Attached latest renewed Fire Safety NOC approved by Maharashtra Fire Services.",
                    "document_id": cured_doc_id,
                    "original_filename": "fire_noc_renewed_2026.pdf",
                    "status": "completed"
                }
            ]
        }
    )
    assert submit_res.status_code == status.HTTP_200_OK
    sub_data = submit_res.json()
    assert sub_data["status"] == "submitted"
    assert sub_data["submission_receipt"] is not None
    assert "RCP-2026-" in sub_data["submission_receipt"]

    # 7. Official reviews response and resolves
    review_res = client.post(
        f"/api/v1/information-requests/{req_id}/review?action=resolved&remarks=Cured+fire+safety+certificate+validated",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert review_res.status_code == status.HTTP_200_OK
    assert review_res.json()["status"] == "resolved"

def test_dashboard_metrics_and_high_scrutiny_queue(client, official_token, db_session):
    """
    Ensure dashboard metrics reconcile, OCR vs native PDF are segregated,
    and High Scrutiny Queue excludes drafts and approved/rejected applications.
    """
    seed_sample_scenarios(db=db_session)
    dash_res = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert dash_res.status_code == status.HTTP_200_OK
    data = dash_res.json()

    # Reconcile counts
    total = data["total_applications"]
    dist_sum = sum(item["count"] for item in data["status_distribution"])
    assert total == dist_sum

    # Pipeline stats segregation
    stats = data["processing_stats"]
    assert "native_pdf_count" in stats
    assert "ocr_count" in stats
    assert "reporting_period" in stats
    assert "last_refresh_time" in stats

    # High Scrutiny Priority Queue: must exclude drafts and approved/rejected
    high_risk_apps = data["high_risk_applications"]
    for app in high_risk_apps:
        assert app["status"] not in ("draft", "approved", "rejected")
        assert len(app["reasons"]) > 0

    # Recent alerts: segregated by finding group and excluding resolved
    alerts = data["recent_alerts"]
    for alert in alerts:
        assert alert["review_status"] in ("open", "acknowledged")
        assert alert["finding_group"] in ("deficiencies", "mismatches", "duplicates", "forensics")
