from datetime import date
import pytest
from backend.app.engines.validator import validate_application_documents

def test_validator_with_injected_today():
    today = date(2026, 10, 27)

    checklist_items = [
        {"doc_type": "land_document", "mandatory": True, "validity_required": False, "description": "Land Title Deed"},
        {"doc_type": "fire_noc", "mandatory": True, "validity_required": True, "description": "Fire Safety NOC"},
        {"doc_type": "society_registration", "mandatory": True, "validity_required": False, "description": "Society Registration"}
    ]

    # Documents: land deed present, fire noc present but expired in 2025, society registration missing
    documents = [
        {"id": 1, "doc_type": "land_document", "page_count": 3, "superseded_by": None},
        {"id": 2, "doc_type": "fire_noc", "page_count": 1, "superseded_by": None}
    ]

    extracted_fields = {
        1: {"land_area_acres": "3.5", "survey_number": "42/A"},
        2: {"reference_no": "CFO/2024/11", "validity_date": "2025-06-30"} # Expired relative to 2026-10-27
    }

    results = validate_application_documents(
        checklist_items=checklist_items,
        documents=documents,
        extracted_fields_by_doc=extracted_fields,
        today=today
    )

    results_by_type = {r.doc_type: r for r in results}

    # 1. Land document should be Valid
    assert results_by_type["land_document"].status == "valid"
    assert len(results_by_type["land_document"].flags) == 0

    # 2. Fire NOC should be Expired
    assert results_by_type["fire_noc"].status == "expired"
    expired_flags = [f for f in results_by_type["fire_noc"].flags if f["category"] == "expired"]
    assert len(expired_flags) == 1
    assert expired_flags[0]["severity"] == "critical"
    assert "2025-06-30" in expired_flags[0]["explanation"]

    # 3. Society registration should be Missing
    assert results_by_type["society_registration"].status == "missing"
    missing_flags = [f for f in results_by_type["society_registration"].flags if f["category"] == "missing"]
    assert len(missing_flags) == 1
    assert missing_flags[0]["severity"] == "critical"

def test_validator_incomplete_fields():
    checklist_items = [
        {"doc_type": "land_document", "mandatory": True, "validity_required": False, "description": "Land Title Deed"}
    ]
    # Land document uploaded but missing survey_number
    documents = [{"id": 10, "doc_type": "land_document", "page_count": 2, "superseded_by": None}]
    extracted_fields = {10: {"land_area_acres": "4.0"}} # missing survey_number

    results = validate_application_documents(
        checklist_items=checklist_items,
        documents=documents,
        extracted_fields_by_doc=extracted_fields
    )

    assert results[0].status == "incomplete"
    assert "survey_number" in results[0].missing_fields
    incomplete_flags = [f for f in results[0].flags if f["category"] == "incomplete"]
    assert len(incomplete_flags) == 1
