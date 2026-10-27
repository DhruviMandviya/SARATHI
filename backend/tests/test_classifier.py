import pytest
from backend.app.engines.classifier import classify_document

def test_classify_land_document():
    sample_text = """
    REGISTERED SALE DEED
    Registered at Sub-Registrar Office, Haveli, Pune.
    This deed of sale is made between the Vendor and Apex Education Trust.
    Schedule of Property: Survey No. 42/1, measuring 3.5 Acres of institutional land.
    """
    res = classify_document(sample_text, filename="land_title_deed.pdf")
    assert res.doc_type == "land_document"
    assert res.confidence >= 0.50
    assert "sale deed" in res.matched_keywords or "survey no" in res.matched_keywords

def test_classify_fire_noc():
    sample_text = """
    OFFICE OF THE CHIEF FIRE OFFICER
    NO OBJECTION CERTIFICATE / FIRE SAFETY CLEARANCE
    Certified that the institution premises has complied with all fire prevention and life safety measures.
    Valid up to: 31-12-2026.
    """
    res = classify_document(sample_text, filename="fire_clearance_noc.pdf")
    assert res.doc_type == "fire_noc"
    assert res.confidence >= 0.50

def test_classify_society_registration():
    sample_text = """
    GOVERNMENT OF MAHARASHTRA
    CERTIFICATE OF REGISTRATION
    Registration No: MAH/1234/2015
    Under the Societies Registration Act, XXI of 1860.
    In the matter of: Apex Education Trust.
    """
    res = classify_document(sample_text, filename="society_cert.pdf")
    assert res.doc_type == "society_registration"
    assert res.confidence >= 0.50

def test_classify_unknown_and_low_confidence():
    garbage_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Random generic essay."
    res = classify_document(garbage_text, filename="random_essay.pdf")
    assert res.doc_type == "unknown"
    assert res.needs_review is True
    assert res.confidence < 0.35

def test_classify_slot_mismatch_detection():
    # User uploaded a fire safety certificate under the 'land_document' checklist slot
    fire_text = """
    GOVERNMENT FIRE DEPARTMENT
    FIRE SAFETY CLEARANCE & NO OBJECTION CERTIFICATE
    Chief Fire Officer hereby certifies safety systems.
    Valid up to: 2027-05-30.
    """
    res = classify_document(fire_text, filename="scan_01.pdf", uploaded_slot="land_document")
    assert res.doc_type == "fire_noc"
    assert res.mismatch_flag is not None
    assert res.mismatch_flag["category"] == "mismatch"
    assert "Document Type Slot Mismatch" in res.mismatch_flag["title"]
