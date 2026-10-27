import pytest
import imagehash
from PIL import Image
from backend.app.engines.duplicates import check_document_duplicates

def test_exact_sha256_cross_institution_is_critical():
    current_doc = {
        "id": 101,
        "doc_type": "land_document",
        "original_filename": "land_deed.pdf",
        "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "phash": "ffff0000ffff0000"
    }

    # Reused by Institution 2 (current is Institution 1)
    candidates = [
        {
            "id": 202,
            "doc_type": "land_document",
            "original_filename": "copied_land_deed.pdf",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "phash": "ffff0000ffff0000",
            "institution_id": 2
        }
    ]

    flags = check_document_duplicates(
        current_doc=current_doc,
        candidate_docs=candidates,
        current_institution_id=1
    )

    assert len(flags) == 1
    flag = flags[0]
    assert flag["category"] == "duplicate"
    assert flag["severity"] == "critical"
    assert "Cross-Institution Document Reuse" in flag["title"]
    assert flag["evidence"]["is_cross_institution"] is True

def test_template_awareness_affidavit_downgrades_to_info():
    """
    Standard prescribed affidavit template used by two institutions:
    Visual layout is nearly identical (low pHash distance), but particulars differ.
    Must produce Info flag, NEVER Critical!
    """
    current_doc = {
        "id": 301,
        "doc_type": "affidavit",
        "original_filename": "apex_affidavit.pdf",
        "sha256": "hash_111",
        "phash": "ffff8888ffff8888"
    }

    candidates = [
        {
            "id": 302,
            "doc_type": "affidavit",
            "original_filename": "zenith_affidavit.pdf",
            "sha256": "hash_222",
            "phash": "ffff8888ffff8880", # Hamming distance is 1 (visual near-match)
            "institution_id": 2
        }
    ]

    current_fields = {
        "institution_name": "Apex Institute of Technology",
        "deponent_name": "Dr. Ramesh Sharma",
        "affidavit_stamp_value_inr": "100"
    }

    candidate_fields = {
        302: {
            "institution_name": "Zenith College of Engineering",
            "deponent_name": "Dr. Anand Rao",
            "affidavit_stamp_value_inr": "100"
        }
    }

    flags = check_document_duplicates(
        current_doc=current_doc,
        candidate_docs=candidates,
        current_fields=current_fields,
        candidate_fields_by_doc=candidate_fields,
        current_institution_id=1
    )

    assert len(flags) == 1
    flag = flags[0]
    assert flag["category"] == "duplicate"
    # Key acceptance criterion: scenario H must NOT be Critical!
    assert flag["severity"] == "info"
    assert "Standard Statutory Template" in flag["title"]
    assert flag["evidence"]["match_type"] == "standard_template"

def test_unrelated_documents_produce_no_duplicates():
    current_doc = {
        "id": 401,
        "doc_type": "fire_noc",
        "sha256": "unique_hash_a",
        "phash": "0000000000000000"
    }
    candidates = [
        {
            "id": 402,
            "doc_type": "land_document",
            "sha256": "unique_hash_b",
            "phash": "ffffffffffffffff",
            "institution_id": 1
        }
    ]
    flags = check_document_duplicates(current_doc=current_doc, candidate_docs=candidates)
    assert len(flags) == 0
