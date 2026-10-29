import pytest
from fastapi import status
from backend.app.models.application import Application

def test_official_decision_flow(client, institution_token, official_token):
    # 1. Create Application
    create_res = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "application_type": "new_institute",
            "academic_year": "2025-2026",
            "declared_details": {
                "institution_name": "Decision Test College",
                "land_area_acres": 4.0
            }
        }
    )
    assert create_res.status_code in (200, 201)
    app_id = create_res.json()["id"]

    # 2. Institution tries to make decision -> 403 Forbidden
    inst_dec = client.post(
        f"/api/v1/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={"outcome": "approved", "remarks": "Trying to self-approve"}
    )
    assert inst_dec.status_code == status.HTTP_403_FORBIDDEN

    # 3. Official tries with empty/short remarks -> 400 Bad Request
    empty_rem = client.post(
        f"/api/v1/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {official_token}"},
        json={"outcome": "approved", "remarks": "Ok"}
    )
    assert empty_rem.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)

    # 4. Official approves with substantive remarks -> 200 OK
    valid_dec = client.post(
        f"/api/v1/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {official_token}"},
        json={
            "outcome": "approved",
            "remarks": "All land documents, fire NOC, and instructional built-up area meet AICTE APH requirements."
        }
    )
    assert valid_dec.status_code == status.HTTP_200_OK
    data = valid_dec.json()
    assert data["outcome"] == "approved"
    assert "APH requirements" in data["remarks"]

    # 5. Verify application status was updated
    get_app = client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert get_app.json()["status"] == "approved"

def test_dashboard_summary_live_metrics(client, official_token):
    res = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_applications" in data
    assert "status_distribution" in data
    assert "recent_alerts" in data
    assert "high_risk_applications" in data
    assert "processing_stats" in data
    assert isinstance(data["status_distribution"], list)

def test_audit_trail_rbac_and_append_only(client, institution_token, official_token, auditor_token):
    # 1. Institution tries to access audit trail -> 403 Forbidden
    inst_res = client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert inst_res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Official accesses audit trail -> 200 OK
    off_res = client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert off_res.status_code == 200
    logs = off_res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0  # Should have seed / previous test events

    # 3. Auditor accesses audit trail -> 200 OK
    aud_res = client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert aud_res.status_code == 200

    # 4. Verify no PUT or DELETE routes exist on /audit
    put_res = client.put("/api/v1/audit/1", headers={"Authorization": f"Bearer {official_token}"})
    assert put_res.status_code in (404, 405)

    del_res = client.delete("/api/v1/audit/1", headers={"Authorization": f"Bearer {official_token}"})
    assert del_res.status_code in (404, 405)
