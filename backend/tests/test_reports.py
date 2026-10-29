import pytest
from backend.app.models.application import Application
from backend.app.models.finding import Flag
from backend.app.engines.risk import RiskEngine
from backend.app.services.pdf_report import generate_application_pdf_report
from backend.app.services.deficiency_letter import generate_deficiency_letter_text

def test_risk_scoring_calculation(db_session):
    app = Application(
        institution_id=1,
        application_no="APP-TEST-RISK-01",
        academic_year="2025-2026",
        type="new_institute",
        status="under_verification",
        declared_details={"institution_name": "Risk Test Institute"}
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Add 1 critical flag and 1 warning flag
    flag1 = Flag(
        application_id=app.id,
        category="duplicate",
        severity="critical",
        title="Cross-Institution Duplicate Title Deed",
        explanation="SHA-256 hash collision with another institutional application.",
        evidence={"hash": "abcd"},
        confidence=1.0,
        confidence_meaning="Exact cryptographic hash match",
        status="open"
    )
    flag2 = Flag(
        application_id=app.id,
        category="mismatch",
        severity="warning",
        title="Land Area Tolerance Exceeded",
        explanation="Declared 3.5 acres vs Extracted 2.8 acres exceeds 10% tolerance.",
        evidence={"declared": 3.5, "extracted": 2.8},
        confidence=0.88,
        confidence_meaning="Fuzzy field extraction comparison",
        status="open"
    )
    db_session.add_all([flag1, flag2])
    db_session.commit()

    engine = RiskEngine(db_session)
    breakdown = engine.calculate_application_risk(app.id)

    # Critical (+25) + Warning (+10) = 35 points
    assert breakdown["score"] >= 35
    assert breakdown["band"] in ["Medium", "High"]
    assert breakdown["critical_flags_count"] >= 1
    assert breakdown["warning_flags_count"] >= 1
    assert len(breakdown["top_contributing_factors"]) >= 2
    assert "decides" in breakdown["philosophy_disclaimer"].lower()

def test_pdf_report_generation(db_session):
    app = Application(
        institution_id=1,
        application_no="APP-TEST-PDF-01",
        academic_year="2025-2026",
        type="new_institute",
        status="under_verification",
        declared_details={"institution_name": "PDF Test Institute"}
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    pdf_bytes = generate_application_pdf_report(app.id, db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

def test_deficiency_letter_generation(db_session):
    app = Application(
        institution_id=1,
        application_no="APP-TEST-DEF-01",
        academic_year="2025-2026",
        type="new_institute",
        status="needs_review",
        declared_details={"institution_name": "Deficiency Test College"}
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    letter = generate_deficiency_letter_text(app.id, db_session)
    assert letter["application_id"] == app.id
    assert "AICTE" in letter["letter_text"]
    assert "fifteen (15) days" in letter["letter_text"]
    assert letter["cure_deadline"] is not None

def test_reports_api_endpoints(client, institution_token, official_token):
    # Create application
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

    # 1. Report JSON
    rep_res = client.get(
        f"/api/v1/applications/{app_id}/report",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert rep_res.status_code == 200
    assert "risk_score" in rep_res.json()

    # 2. PDF Download
    pdf_res = client.get(
        f"/api/v1/applications/{app_id}/report.pdf",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")

    # 3. Deficiency Letter
    let_res = client.get(
        f"/api/v1/applications/{app_id}/deficiency-letter",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert let_res.status_code == 200
    assert "letter_text" in let_res.json()
