import pytest
from backend.app.engines.verifiers.base import VerificationOutcome
from backend.app.engines.verifiers.mock_building_plan import BuildingPlanVerifier
from backend.app.engines.verifiers.mock_fire_noc import FireNOCVerifier
from backend.app.engines.verifiers.mock_society_reg import SocietyRegistrationVerifier
from backend.app.engines.verifiers.mock_env_clearance import EnvironmentClearanceVerifier
from backend.app.engines.verifiers import verify_document

def test_building_plan_verifier_outcomes():
    v = BuildingPlanVerifier()

    # 1. Verified
    res_ok = v.verify("SAN-2024-5541")
    assert res_ok.status == "verified"
    assert res_ok.is_simulated is True
    assert "approved" in res_ok.message.lower()

    # 2. Not Verified / Rejected
    res_rej = v.verify("SAN-2024-REJ")
    assert res_rej.status == "not_verified"
    assert res_rej.is_simulated is True

    # 3. In Progress
    res_prog = v.verify("SAN-2024-PROG")
    assert res_prog.status == "in_progress"
    assert res_prog.is_simulated is True

    # 4. Pending / Missing
    res_pend = v.verify(None)
    assert res_pend.status == "pending"
    assert res_pend.is_simulated is True

def test_fire_noc_verifier_outcomes():
    v = FireNOCVerifier()

    res_ok = v.verify("FS-NOC-7821")
    assert res_ok.status == "verified"
    assert res_ok.is_simulated is True

    res_rej = v.verify("FS-NOC-00")
    assert res_rej.status == "not_verified"
    assert res_rej.is_simulated is True

    res_pend = v.verify("FS-NOC-PEND")
    assert res_pend.status == "pending"
    assert res_pend.is_simulated is True

def test_society_reg_verifier_outcomes():
    v = SocietyRegistrationVerifier()

    res_ok = v.verify("SOC-MAH-2015-88")
    assert res_ok.status == "verified"
    assert res_ok.is_simulated is True

    res_rej = v.verify("SOC-MAH-2015-REJ")
    assert res_rej.status == "not_verified"
    assert res_rej.is_simulated is True

def test_environment_clearance_verifier_outcomes():
    v = EnvironmentClearanceVerifier()

    res_ok = v.verify("CTE-ENV-9912")
    assert res_ok.status == "verified"
    assert res_ok.is_simulated is True

    res_rej = v.verify("CTE-ENV-REJ")
    assert res_rej.status == "not_verified"
    assert res_rej.is_simulated is True

def test_unsupported_document_type_defaults_to_pending():
    res = verify_document("unknown_doc_type", "REF123")
    assert res.status == "pending"
    assert res.is_simulated is True
    assert "no automated verification adapter" in res.message.lower()

def test_verification_api_endpoint(client, institution_token, official_token):
    # Create draft application
    create_res = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "application_type": "new_institute",
            "academic_year": "2025-2026",
            "declared_details": {
                "institution_name": "Apex Engineering College",
                "land_area_acres": 3.2
            }
        }
    )
    assert create_res.status_code in (200, 201)
    app_id = create_res.json()["id"]

    # Call verification endpoint
    ver_res = client.get(
        f"/api/v1/applications/{app_id}/verification",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert ver_res.status_code == 200
    assert isinstance(ver_res.json(), list)
