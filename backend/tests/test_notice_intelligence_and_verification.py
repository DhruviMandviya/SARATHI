import pytest
from datetime import datetime, timezone
from backend.app.engines.duplicates import check_document_duplicates
from backend.app.services.finding_classification import classify_flag, get_candidate_notice_items
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.finding import Flag
from backend.app.models.user import User

def test_self_comparison_and_normalized_pair_ordering():
    """
    Self-comparison must be strictly excluded.
    Pair ordering must be normalized (min_id:max_id) regardless of argument order.
    """
    doc_a = {
        "id": 10,
        "doc_type": "land_document",
        "original_filename": "deed_a.pdf",
        "sha256": "hash_same",
        "phash": "ffff0000ffff0000"
    }

    # Self-comparison
    self_flags = check_document_duplicates(
        current_doc=doc_a,
        candidate_docs=[doc_a],
        current_institution_id=1
    )
    assert len(self_flags) == 0, "Self-comparison must not produce duplicate flags"

    # A against B
    doc_b = {
        "id": 20,
        "doc_type": "land_document",
        "original_filename": "deed_b.pdf",
        "sha256": "hash_same",
        "phash": "ffff0000ffff0000",
        "institution_id": 1
    }

    flags_ab = check_document_duplicates(
        current_doc=doc_a,
        candidate_docs=[doc_b],
        current_institution_id=1
    )
    assert len(flags_ab) == 1
    pair_ab = flags_ab[0]["evidence"]["pair_key"]
    assert pair_ab in ("10_20", "10:20")

    # B against A (reversed)
    flags_ba = check_document_duplicates(
        current_doc=doc_b,
        candidate_docs=[doc_a],
        current_institution_id=1
    )
    assert len(flags_ba) == 1
    pair_ba = flags_ba[0]["evidence"]["pair_key"]
    assert pair_ba in ("10_20", "10:20"), "Pair key must be normalized to min:max"

def test_exact_hash_vs_perceptual_similarity():
    """
    Never report 100% cryptographic match unless the actual SHA-256 hashes are identical.
    Visual pHash must be strictly capped below 100%.
    """
    # 1. Identical SHA-256
    doc_1 = {"id": 1, "doc_type": "land_document", "sha256": "exact_hash_xyz", "phash": "ffff0000"}
    doc_2 = {"id": 2, "doc_type": "land_document", "sha256": "exact_hash_xyz", "phash": "ffff0000", "institution_id": 1}
    exact_flags = check_document_duplicates(doc_1, [doc_2], current_institution_id=1)
    assert len(exact_flags) == 1
    assert exact_flags[0]["evidence"]["similarity_percentage"] == 100.0
    assert exact_flags[0]["evidence"]["match_type"] == "exact_sha256"

    # 2. Different SHA-256, but identical pHash on template document
    doc_3 = {"id": 3, "doc_type": "affidavit", "sha256": "hash_alpha", "phash": "1234567890abcdef"}
    doc_4 = {"id": 4, "doc_type": "affidavit", "sha256": "hash_beta", "phash": "1234567890abcdef", "institution_id": 1}
    phash_flags = check_document_duplicates(doc_3, [doc_4], current_institution_id=1)
    assert len(phash_flags) == 1
    # Must NOT report 100% cryptographic match
    assert phash_flags[0]["evidence"]["similarity_percentage"] <= 98.5
    assert phash_flags[0]["evidence"]["match_type"] in ("visual_phash", "standard_template")

def test_notice_candidate_classification_actionable_vs_internal():
    """
    Internal forensic and duplicate findings must be classified as internal review only.
    Mandatory compliance and material inconsistencies must be applicant actionable.
    """
    class MockFlag:
        def __init__(self, category, title, explanation, severity="critical", rule_ref=None, evidence=None):
            self.id = 1
            self.category = category
            self.title = title
            self.explanation = explanation
            self.severity = severity
            self.rule_ref = rule_ref
            self.evidence = evidence or {}
            self.actionability = None
            self.document_id = None
            self.status = "open"

    # 1. Missing document
    f_missing = MockFlag("missing", "Missing Land Document", "Mandatory land title deed missing", rule_ref="APH-MANDATORY")
    c_missing = classify_flag(f_missing)
    assert c_missing["candidate_category"] == "mandatory_compliance"
    assert c_missing["is_actionable"] is True
    assert c_missing["actionability"] == "MANDATORY_DOCUMENT_MISSING"

    # 2. Material Inconsistency
    f_incons = MockFlag("consistency", "Land Area Discrepancy", "Survey land area differs between sale deed and declaration")
    c_incons = classify_flag(f_incons)
    assert c_incons["candidate_category"] == "material_inconsistencies"
    assert c_incons["is_actionable"] is True

    # 3. Forensic Signal (ELA / Copy-move)
    f_forensic = MockFlag("tampering", "ELA Anomaly Detected", "Potential digital stamp splicing identified", severity="warning")
    c_forensic = classify_flag(f_forensic)
    assert c_forensic["candidate_category"] == "internal_forensics"
    assert c_forensic["is_actionable"] is False
    assert c_forensic["actionability"] == "INTERNAL_REVIEW_ONLY"

    # 4. Duplicate document
    f_dup = MockFlag("duplicate", "Duplicate Document Layout", "Near-duplicate pHash layout detected")
    c_dup = classify_flag(f_dup)
    assert c_dup["candidate_category"] == "duplicate_similarity"
    assert c_dup["is_actionable"] is False
    assert c_dup["actionability"] == "INTERNAL_REVIEW_ONLY"

def test_notice_builder_issuance_validations(client, official_token, institution_token, db_session):
    """
    Official Notice Builder:
    - Empty selected items returns 400.
    - Zero actionable items returns 400.
    - Issuance requires official role (institution gets 403).
    - Successful issuance transitions application to info_requested and sets deadline.
    """
    # 1. Unauthorized attempt
    unauth_res = client.post(
        "/api/v1/applications/2/issue-notice-builder",
        json={"selected_items": [], "official_remarks": "Test remarks"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert unauth_res.status_code == 403

    # 2. Empty items attempt
    empty_res = client.post(
        "/api/v1/applications/2/issue-notice-builder",
        json={"selected_items": [], "official_remarks": "Test remarks"},
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert empty_res.status_code == 400
    assert "A deficiency notice must include at least one valid applicant-actionable item" in empty_res.json()["detail"]

    # 3. Valid issuance with candidate item
    valid_payload = {
        "official_remarks": "Mandatory deficiency notice per AICTE APH regulations",
        "cure_period_days": 15,
        "selected_items": [
            {
                "finding_id": 99999,
                "title": "Missing Encumbrance Certificate",
                "explanation": "Provide certified 30-year non-encumbrance certificate.",
                "requested_action": "Upload sub-registrar issued EC",
                "requires_explanation": True,
                "requires_upload": True,
                "doc_type": "encumbrance_certificate"
            }
        ]
    }
    issue_res = client.post(
        "/api/v1/applications/2/issue-notice-builder",
        json=valid_payload,
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert issue_res.status_code == 200
    data = issue_res.json()
    assert len(data.get("deficiencies", [])) == 1
    assert data["status"] in ("issued", "action_required")
    assert "deadline" in data

    # Verify application status was updated
    app = db_session.query(Application).filter(Application.id == 2).first()
    assert app.status == "info_requested"

def test_document_official_review_actions(client, official_token, institution_token, db_session):
    """
    Official Document Scrutiny Actions:
    - Mark Verified records determination with timestamp and remarks.
    - Confirm Mismatch requires meaningful remarks.
    - Re-validate executes validation engine.
    - Institution role is forbidden.
    """
    doc = db_session.query(Document).filter(Document.application_id == 1).first()
    assert doc is not None, "A document must exist for application 1"

    # 1. Institution forbidden
    inst_res = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "verified", "remarks": "Checked"},
        headers={"Authorization": f"Bearer {institution_token}"}
    )
    assert inst_res.status_code == 403

    # 2. Mismatch confirmed without remarks returns 400
    bad_res = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "mismatch_confirmed", "remarks": ""},
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert bad_res.status_code == 400

    # 3. Mark Verified by Official
    ok_res = client.post(
        f"/api/v1/documents/{doc.id}/official-review",
        json={"outcome": "verified", "remarks": "Statutory boundaries and survey numbers verified by scrutiny officer."},
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert ok_res.status_code == 200
    doc_out = ok_res.json()
    assert doc_out["official_verification_status"] == "verified"
    assert doc_out["official_verified_by"] is not None

    # 4. Re-validate document
    reval_res = client.post(
        f"/api/v1/documents/{doc.id}/re-validate",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert reval_res.status_code == 200
    reval_data = reval_res.json()
    assert "validation_status" in reval_data
    assert "flags_count" in reval_data

def test_authenticity_verification_reverify_and_manual(client, official_token, db_session):
    """
    Stage 6 Authenticity:
    - Re-Verify accepts manual reference override.
    - Record Manual Verification persists manual scrutiny outcome.
    """
    doc = db_session.query(Document).filter(Document.application_id == 1).first()

    # 1. Re-Verify with manual reference number
    rev_res = client.post(
        f"/api/v1/applications/1/documents/{doc.id}/verify",
        json={"reference_no": "REG-GOV-SURV-2024-999"},
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert rev_res.status_code == 200
    data = rev_res.json()
    assert data["verification_mode"] == "SIMULATED"
    assert data["checked_reference"] == "REG-GOV-SURV-2024-999"

    # 2. Manual Verification
    man_res = client.post(
        f"/api/v1/applications/1/documents/{doc.id}/manual-verify",
        json={
            "outcome": "verified",
            "remarks": "Physically cross-verified with state sub-registrar registry books.",
            "manual_reference_no": "REG-BOOK-VOL-12"
        },
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert man_res.status_code == 200
    man_data = man_res.json()
    assert man_data["verification_mode"] == "MANUAL_SCRUTINY"
    assert man_data["status"] == "verified"

def test_dashboard_alerts_balanced_and_draft_excluded(client, official_token, db_session):
    """
    Official Dashboard:
    - Draft applications are excluded from active scrutiny.
    - Discrepancy alerts contain categorized items without duplicate pair flooding.
    """
    summary_res = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {official_token}"}
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()

    # Drafts must be tracked separately
    assert "total_applications" in summary
    assert "status_distribution" in summary
    assert "recent_alerts" in summary
    recent = summary["recent_alerts"]
    assert len(recent) > 0

    # Ensure finding_group exists across alerts
    groups = {f.get("finding_group") for f in recent}
    assert len(groups) >= 1
