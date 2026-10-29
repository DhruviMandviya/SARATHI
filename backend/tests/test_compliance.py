import pytest
from backend.app.engines.compliance import ComplianceEngine
from backend.app.models.application import Application
from backend.app.models.compliance import ComplianceRule, ComplianceResult

def test_compliance_engine_evaluation_and_bounds(db_session):
    # Setup test application
    app = Application(
        institution_id=1,
        application_no="APP-TEST-COMP-01",
        academic_year="2025-2026",
        type="new_institute",
        status="submitted",
        declared_details={
            "land_area_acres": 3.0,          # Required: 2.5 -> Compliant
            "built_up_area_sqm": 3500.0,     # Required: 4000.0 -> Non-compliant (deficit 500)
            "student_faculty_ratio": 18.0,   # Max: 20.0 -> Compliant
            "affidavit_stamp_value_inr": 100 # Min: 100 -> Compliant
            # labs_count missing -> Needs Review
        }
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    engine = ComplianceEngine(db_session)
    results = engine.evaluate_application(app.id)

    res_by_key = {}
    for r in results:
        rule = db_session.query(ComplianceRule).filter(ComplianceRule.id == r.rule_id).first()
        res_by_key[rule.rule_key] = r

    # 1. min_land_area should be compliant
    assert "min_land_area" in res_by_key
    assert res_by_key["min_land_area"].outcome == "compliant"
    assert "3.0" in res_by_key["min_land_area"].provided_value

    # 2. min_built_up_area should be non_compliant with deficit explanation
    assert "min_built_up_area" in res_by_key
    assert res_by_key["min_built_up_area"].outcome == "non_compliant"
    assert "Deficit: 500" in res_by_key["min_built_up_area"].explanation

    # 3. faculty_student_ratio should be compliant
    assert "faculty_student_ratio" in res_by_key
    assert res_by_key["faculty_student_ratio"].outcome == "compliant"

    # 4. min_laboratories was not provided -> should be needs_review
    assert "min_laboratories" in res_by_key
    assert res_by_key["min_laboratories"].outcome == "needs_review"
    assert "Not provided" in res_by_key["min_laboratories"].provided_value

def test_admin_non_mutating_rule_versioning(client, admin_token):
    # Get active rules
    get_res = client.get(
        "/api/v1/admin/rules",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_res.status_code == 200
    rules = get_res.json()
    assert len(rules) > 0

    target_rule = rules[0]
    rule_id = target_rule["id"]
    old_version = target_rule["version"]

    # Update parameters to create a new version
    new_params = dict(target_rule["parameters"])
    new_params["min_value"] = 3.5

    put_res = client.put(
        f"/api/v1/admin/rules/{rule_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "parameters": new_params,
            "active": True,
            "verified_against_handbook": True
        }
    )
    assert put_res.status_code == 200
    updated_rule = put_res.json()

    assert updated_rule["version"] == old_version + 1
    assert updated_rule["parameters"]["min_value"] == 3.5
    assert updated_rule["verified_against_handbook"] is True
    assert updated_rule["id"] != rule_id  # New ID created, non-mutating!
