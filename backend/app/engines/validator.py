from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.app.engines.extractor import parse_date_string

class DocumentValidationResult:
    def __init__(
        self,
        doc_type: str,
        document_id: Optional[int],
        status: str,  # valid, incomplete, expired, mismatch, missing
        remarks: str,
        flags: List[Dict[str, Any]],
        missing_fields: List[str]
    ):
        self.doc_type = doc_type
        self.document_id = document_id
        self.status = status
        self.remarks = remarks
        self.flags = flags
        self.missing_fields = missing_fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "document_id": self.document_id,
            "status": self.status,
            "remarks": self.remarks,
            "flags": self.flags,
            "missing_fields": self.missing_fields
        }

EXPECTED_FIELDS_BY_DOC_TYPE = {
    "land_document": ["land_area_acres", "survey_number"],
    "building_plan": ["built_up_area_sqm"],
    "fire_noc": ["reference_no", "validity_date"],
    "society_registration": ["registration_no"],
    "affidavit": ["affidavit_stamp_value_inr"]
}

def validate_application_documents(
    checklist_items: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    extracted_fields_by_doc: Dict[int, Dict[str, str]],
    today: Optional[date] = None
) -> List[DocumentValidationResult]:
    """
    Validates documents against checklist items and extracts validity/completeness.
    Takes injectable `today` for deterministic testing.
    """
    check_date = today or date.today()
    results: List[DocumentValidationResult] = []

    # Map active documents by doc_type
    docs_by_type = {doc.get("doc_type"): doc for doc in documents if not doc.get("superseded_by")}

    for item in checklist_items:
        doc_type = item["doc_type"]
        mandatory = bool(item.get("mandatory", True))
        validity_required = bool(item.get("validity_required", False))
        description = item.get("description", doc_type)

        doc = docs_by_type.get(doc_type)

        # 1. Missing check
        if not doc:
            if mandatory:
                flag = {
                    "category": "missing",
                    "severity": "critical",
                    "title": f"Mandatory Document Missing: {description}",
                    "explanation": f"Mandatory document '{description}' ({doc_type}) has not been uploaded. Council regulations prohibit proceeding without this prerequisite.",
                    "evidence": {"doc_type": doc_type, "mandatory": True},
                    "confidence": 1.0,
                    "confidence_meaning": "Deterministic checklist inspection",
                    "rule_ref": f"Checklist_{doc_type}"
                }
                results.append(DocumentValidationResult(
                    doc_type=doc_type,
                    document_id=None,
                    status="missing",
                    remarks=f"Mandatory document missing: {description}",
                    flags=[flag],
                    missing_fields=[]
                ))
            else:
                results.append(DocumentValidationResult(
                    doc_type=doc_type,
                    document_id=None,
                    status="missing",
                    remarks="Optional document not uploaded",
                    flags=[],
                    missing_fields=[]
                ))
            continue

        doc_id = doc.get("id")
        fields = extracted_fields_by_doc.get(doc_id, {})
        flags: List[Dict[str, Any]] = []
        status = "valid"
        remarks_list = []

        # 2. Key fields completeness check
        expected_fields = EXPECTED_FIELDS_BY_DOC_TYPE.get(doc_type, [])
        missing_fields = [f for f in expected_fields if not fields.get(f)]

        if missing_fields:
            status = "incomplete"
            clean_names = [f.replace("_", " ") for f in missing_fields]
            rem = f"Incomplete document: Required key fields not detected ({', '.join(clean_names)})."
            remarks_list.append(rem)
            flags.append({
                "category": "incomplete",
                "severity": "warning",
                "title": f"Incomplete Document: {description}",
                "explanation": rem,
                "evidence": {"doc_type": doc_type, "missing_fields": missing_fields},
                "confidence": 0.88,
                "confidence_meaning": "Key parameter regex pattern search in extracted document text",
                "rule_ref": f"Completeness_{doc_type}"
            })

        # 3. Validity / Expiry check
        if validity_required or "validity_date" in fields:
            val_date_str = fields.get("validity_date")
            if val_date_str:
                parsed_val = parse_date_string(val_date_str)
                if parsed_val:
                    try:
                        exp_dt = datetime.strptime(parsed_val, "%Y-%m-%d").date()
                        if exp_dt < check_date:
                            status = "expired"
                            rem = f"Document validity expired on {parsed_val} (Evaluation reference date: {check_date.isoformat()})."
                            remarks_list.append(rem)
                            flags.append({
                                "category": "expired",
                                "severity": "critical",
                                "title": f"Document Expired: {description}",
                                "explanation": rem,
                                "evidence": {"validity_date": parsed_val, "reference_date": check_date.isoformat()},
                                "confidence": 1.0,
                                "confidence_meaning": "Deterministic date arithmetic comparison against evaluation date",
                                "rule_ref": f"Validity_{doc_type}"
                            })
                    except ValueError:
                        pass
            elif validity_required:
                status = "incomplete"
                rem = "Validity period required by council norms but no expiry date detected on certificate."
                remarks_list.append(rem)

        # 4. Page count sanity check
        page_count = doc.get("page_count", 1)
        if doc_type in ("land_document", "building_plan") and page_count == 1:
            flags.append({
                "category": "quality",
                "severity": "info",
                "title": f"Single-Page Document ({description})",
                "explanation": f"Document has only 1 page. Ensure that complete schedules, boundaries, and official attestation pages are fully scanned.",
                "evidence": {"page_count": page_count},
                "confidence": 0.90,
                "confidence_meaning": "Physical page count inspection",
                "rule_ref": "PageCount_Sanity"
            })

        # 5. Heuristic signature / stamp check
        sig_cue = fields.get("signature_cue", "")
        if "No signature" in sig_cue:
            flags.append({
                "category": "quality",
                "severity": "info",
                "title": "Signature / Attestation Cue Verification",
                "explanation": "Heuristic analysis did not identify explicit signature or seal keywords. Please visually verify official signatory presence.",
                "evidence": {"signature_cue": sig_cue},
                "confidence": 0.60,
                "confidence_meaning": "Heuristic keyword cue search (weak signal - manual verification advised)",
                "rule_ref": "Signature_Cue"
            })

        remarks = "; ".join(remarks_list) if remarks_list else "Document passed initial completeness and validity checks."
        results.append(DocumentValidationResult(
            doc_type=doc_type,
            document_id=doc_id,
            status=status,
            remarks=remarks,
            flags=flags,
            missing_fields=missing_fields
        ))

    return results
