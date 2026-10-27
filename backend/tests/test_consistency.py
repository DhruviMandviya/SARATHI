import pytest
from backend.app.engines.consistency import check_consistency

def test_consistency_matching_names_and_area():
    declared = {
        "institution_name": "Apex Institute of Technology",
        "trust_name": "Apex Education Trust",
        "land_area_acres": 3.5,
        "built_up_area_sqm": 4500.0
    }

    # Document values match or are minor abbreviations
    doc_fields = {
        "land_document": {
            "institution_name": "Apex Institute of Technology",
            "trust_name": "Apex Education Trust",
            "land_area_acres": "3.5"
        },
        "fire_noc": {
            "institution_name": "Apex Inst. of Technology",
            "issue_date": "2025-01-10",
            "validity_date": "2026-12-31"
        }
    }

    flags = check_consistency(declared, doc_fields)
    # Should not produce any mismatch flags
    mismatch_flags = [f for f in flags if f["category"] == "mismatch"]
    assert len(mismatch_flags) == 0

def test_consistency_institution_name_mismatch():
    declared = {
        "institution_name": "Apex Institute of Technology",
        "trust_name": "Apex Education Trust"
    }

    # Fire NOC has completely different institution name
    doc_fields = {
        "fire_noc": {
            "institution_name": "Royal Academy of Technical Sciences"
        }
    }

    flags = check_consistency(declared, doc_fields)
    assert len(flags) > 0
    flag = flags[0]
    assert flag["category"] == "mismatch"
    assert "Apex Institute of Technology" in flag["explanation"]
    assert "Royal Academy of Technical Sciences" in flag["explanation"]
    assert "Similarity" in flag["explanation"]
    assert "similarity_score" in flag["evidence"]

def test_consistency_land_area_tolerance_exceeded():
    declared = {
        "institution_name": "Apex Institute of Technology",
        "land_area_acres": 5.0
    }

    # Land deed has only 2.0 acres (huge variance)
    doc_fields = {
        "land_document": {
            "institution_name": "Apex Institute of Technology",
            "land_area_acres": "2.0"
        }
    }

    flags = check_consistency(declared, doc_fields)
    area_flags = [f for f in flags if "Land Area Discrepancy" in f["title"]]
    assert len(area_flags) == 1
    assert area_flags[0]["severity"] == "critical"
    assert "5.00 Acres" in area_flags[0]["explanation"]
    assert "2.00 Acres" in area_flags[0]["explanation"]

def test_consistency_date_chronology_error():
    declared = {"institution_name": "Apex Institute of Technology"}
    doc_fields = {
        "fire_noc": {
            "institution_name": "Apex Institute of Technology",
            "issue_date": "2027-01-01",
            "validity_date": "2026-01-01" # Issue date is after validity date!
        }
    }

    flags = check_consistency(declared, doc_fields)
    date_flags = [f for f in flags if "Chronological Inconsistency" in f["title"]]
    assert len(date_flags) == 1
    assert date_flags[0]["severity"] == "critical"
