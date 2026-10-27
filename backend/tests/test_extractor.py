import pytest
from backend.app.engines.extractor import (
    extract_fields_from_text,
    normalize_land_area_to_acres,
    parse_date_string
)

def test_unit_normalization():
    # 1 Hectare is approx 2.471 acres
    acres_from_ha = normalize_land_area_to_acres(2.0, "hectares")
    assert abs(acres_from_ha - 4.9421) < 0.05

    # 10,000 Sq.m is approx 2.471 acres
    acres_from_sqm = normalize_land_area_to_acres(10000.0, "sq.m")
    assert abs(acres_from_sqm - 2.471) < 0.05

    # Direct acres
    acres = normalize_land_area_to_acres(3.5, "acres")
    assert acres == 3.5

def test_date_parsing():
    assert parse_date_string("2026-12-31") == "2026-12-31"
    assert parse_date_string("31/12/2026") == "2026-12-31"
    assert parse_date_string("15-08-2025") == "2025-08-15"
    assert parse_date_string("invalid_date_string") is None

def test_extract_land_document_fields():
    text = """
    CONVEYANCE & REGISTERED SALE DEED
    Institution Name: Apex Institute of Technology
    Trust Name: Apex Education Trust
    Land Owner: Ramesh Chandra Gupta
    Schedule of Property: Survey No. 104/2B
    The campus property comprises 3.5 Acres of contiguous land.
    Registered on: 12-04-2022.
    """
    fields = extract_fields_from_text(text, doc_type="land_document")
    field_dict = {f["key"]: f["value"] for f in fields}

    assert "Apex Institute of Technology" in field_dict.get("institution_name", "")
    assert "Apex Education Trust" in field_dict.get("trust_name", "")
    assert field_dict.get("survey_number") == "104/2B"
    assert field_dict.get("land_area_acres") == "3.5"
    assert field_dict.get("registration_date") == "2022-04-12"

def test_extract_fire_noc_fields():
    text = """
    FIRE SAFETY & CLEARANCE CERTIFICATE
    Institution Name: Zenith College of Engineering
    NOC No: CFO/FS/2025/9981
    Dated: 10-01-2025
    Valid up to: 31-12-2026
    """
    fields = extract_fields_from_text(text, doc_type="fire_noc")
    field_dict = {f["key"]: f["value"] for f in fields}

    assert field_dict.get("reference_no") == "CFO/FS/2025/9981"
    assert field_dict.get("validity_date") == "2026-12-31"
    assert field_dict.get("issue_date") == "2025-01-10"

def test_extract_building_plan_fields():
    text = """
    MUNICIPAL CORPORATION SANCTIONED PLAN
    Institution Name: Apex Institute of Technology
    Sanction Order No: MC/BP/2024/451
    Total Built-up Area: 4850.5 sq.m
    """
    fields = extract_fields_from_text(text, doc_type="building_plan")
    field_dict = {f["key"]: f["value"] for f in fields}

    assert field_dict.get("built_up_area_sqm") == "4850.5"
    assert field_dict.get("sanction_number") == "MC/BP/2024/451"
