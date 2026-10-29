import re
from typing import List, Dict, Any, Optional, Tuple
import imagehash
from rapidfuzz import fuzz

KNOWN_TEMPLATE_DOC_TYPES = [
    "affidavit",
    "standard_undertaking",
    "land_document",
    "building_plan",
    "fire_noc",
    "society_registration",
    "env_clearance"
]

def hamming_distance(hash1_str: str, hash2_str: str) -> int:
    try:
        h1 = imagehash.hex_to_hash(hash1_str)
        h2 = imagehash.hex_to_hash(hash2_str)
        return int(h1 - h2)
    except Exception:
        return 999

def check_document_duplicates(
    current_doc: Dict[str, Any],
    candidate_docs: List[Dict[str, Any]],
    current_fields: Optional[Dict[str, str]] = None,
    candidate_fields_by_doc: Optional[Dict[int, Dict[str, str]]] = None,
    current_institution_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates:
    1. Exact duplicates: SHA-256 match
    2. Near-duplicates: pHash Hamming distance <= 8 AND text similarity >= 80%
    3. Template-awareness: If doc_type is in KNOWN_TEMPLATE_DOC_TYPES, compare filled-in fields.
       Downgrade layout-only matches to Info.
    4. Cross-institution vs intra-application: Reusing a document in a different institution
       is Critical, whereas within the same application is Warning/Info.
    """
    flags: List[Dict[str, Any]] = []
    current_doc_id = current_doc.get("id")
    current_sha = current_doc.get("sha256")
    current_phash = current_doc.get("phash")
    current_type = current_doc.get("doc_type")
    current_fields = current_fields or {}
    candidate_fields_by_doc = candidate_fields_by_doc or {}

    is_template_type = current_type in KNOWN_TEMPLATE_DOC_TYPES

    for cand in candidate_docs:
        cand_id = cand.get("id")
        if not cand_id or cand_id == current_doc_id:
            continue

        cand_sha = cand.get("sha256")
        cand_phash = cand.get("phash")
        cand_type = cand.get("doc_type")
        cand_inst_id = cand.get("institution_id")
        is_cross_institution = (
            current_institution_id is not None
            and cand_inst_id is not None
            and current_institution_id != cand_inst_id
        )

        matched_signals = []
        is_exact = False
        is_near = False
        similarity_pct = 0.0

        # Signal 1: Exact SHA-256 Cryptographic Hash
        if current_sha and cand_sha and current_sha == cand_sha:
            is_exact = True
            matched_signals.append("Identical SHA-256 cryptographic hash (100% byte match)")
            similarity_pct = 100.0

        # Signal 2: pHash Visual Similarity (Hamming Distance)
        dist = 999
        if current_phash and cand_phash and (cand_type == current_type or is_exact):
            dist = hamming_distance(current_phash, cand_phash)
            # Evaluate text similarity between extracted fields
            cand_fields = candidate_fields_by_doc.get(cand_id, {})
            t1 = " ".join([str(v) for v in current_fields.values() if v])
            t2 = " ".join([str(v) for v in cand_fields.values() if v])
            text_sim = fuzz.token_sort_ratio(t1, t2) if (t1 and t2) else 0.0

            # For near-duplicate visual matching, require meaningful text/content similarity
            if is_exact:
                pass
            elif (dist <= 4 and text_sim >= 65.0) or (dist <= 8 and text_sim >= 80.0) or (dist <= 6 and is_template_type):
                is_near = True
                matched_signals.append(f"Visual perceptual hash match (Hamming distance {dist} <= 8, text similarity {text_sim:.0f}%)")
                # Perceptual hash can NEVER be 100% cryptographic match unless SHA-256 matches
                calculated_pct = round((1.0 - (dist / 64.0)) * 100, 1)
                similarity_pct = min(98.5, max(similarity_pct, calculated_pct))

        if not (is_exact or is_near):
            continue

        # Signal 3: Template-Awareness evaluation for affidavits and standard government formats
        cand_fields = candidate_fields_by_doc.get(cand_id, {})
        has_shared_particulars = False
        field_differences = []

        if is_template_type and cand_type == current_type:
            # Check unique identifying particulars (deponent, institution, reference numbers)
            unique_identifying_keys = [
                "institution_name",
                "deponent_name",
                "registration_no",
                "reference_no",
                "deed_number",
                "sanction_no",
                "noc_number",
                "survey_number",
                "order_no"
            ]
            matching_identifying_count = 0
            distinct_identifying_count = 0

            for k in unique_identifying_keys:
                v1 = re.sub(r"^[^\w]+|[^\w]+$", "", current_fields.get(k, "").strip().lower())
                v2 = re.sub(r"^[^\w]+|[^\w]+$", "", cand_fields.get(k, "").strip().lower())
                if len(v1) > 2 and len(v2) > 2:
                    if fuzz.ratio(v1, v2) > 80:
                        matching_identifying_count += 1
                    else:
                        distinct_identifying_count += 1
                        field_differences.append(f"{k.replace('_', ' ')} differs ('{v1}' vs '{v2}')")

            # If not exact file match and identifying particulars differ:
            if not is_exact and (distinct_identifying_count > 0 or matching_identifying_count == 0):
                # Legitimate shared standard template format - NOT a defect or fraud
                flags.append({
                    "category": "duplicate",
                    "severity": "info",
                    "actionability": "INTERNAL_REVIEW_ONLY",
                    "title": f"Standard Statutory Template Format Detected ({current_type.replace('_', ' ').title()})",
                    "explanation": (
                        f"Document shares layout similarity (pHash distance {dist}) with another {current_type} "
                        f"(Doc #{cand_id}), but individual institution/deponent particulars legitimately differ ({'; '.join(field_differences[:2]) or 'different applicants'}). "
                        "Expected for AICTE standard prescribed affidavit blanks."
                    ),
                    "evidence": {
                        "current_doc_id": current_doc_id,
                        "matched_doc_id": cand_id,
                        "doc_pair_key": f"{min(current_doc_id or 0, cand_id)}_{max(current_doc_id or 0, cand_id)}",
                        "match_type": "standard_template",
                        "is_cross_institution": is_cross_institution,
                        "similarity_percentage": similarity_pct,
                        "signals": matched_signals,
                        "field_differences": field_differences
                    },
                    "confidence": 0.85,
                    "confidence_meaning": "Template layout detection with unique field differentiation",
                    "rule_ref": "Duplicate_TemplateAware"
                })
                continue
            elif matching_identifying_count > 0 or is_exact:
                has_shared_particulars = True

        # Normalized pair key
        pair_key = f"{min(current_doc_id or 0, cand_id)}_{max(current_doc_id or 0, cand_id)}"

        # Non-template duplicates or identical content reuse
        if is_cross_institution:
            severity = "critical"
            title = f"Cross-Institution Document Reuse Detected (Doc #{cand_id})"
            explanation = (
                f"Document content matches document #{cand_id} previously submitted by a different institution "
                f"(Institution #{cand_inst_id}). Similarity: {similarity_pct:.1f}%. Signals: {', '.join(matched_signals)}."
            )
        else:
            severity = "warning"
            title = f"Duplicate Document within Application (Doc #{cand_id})"
            explanation = (
                f"Document appears identical or near-identical to Doc #{cand_id} within this application. "
                f"Similarity: {similarity_pct:.1f}%. Signals: {', '.join(matched_signals)}."
            )

        flags.append({
            "category": "duplicate",
            "severity": severity,
            "actionability": "INTERNAL_REVIEW_ONLY",
            "title": title,
            "explanation": explanation,
            "evidence": {
                "current_doc_id": current_doc_id,
                "current_filename": current_doc.get("original_filename"),
                "matched_doc_id": cand_id,
                "matched_filename": cand.get("original_filename"),
                "matched_institution_id": cand_inst_id,
                "doc_pair_key": pair_key,
                "pair_key": pair_key,
                "match_type": "exact_sha256" if is_exact else "visual_phash",
                "is_cross_institution": is_cross_institution,
                "similarity_percentage": similarity_pct,
                "signals": matched_signals
            },
            "confidence": 1.0 if is_exact else 0.90,
            "confidence_meaning": "Deterministic cryptographic hash equality" if is_exact else "Perceptual image hash Hamming distance",
            "rule_ref": "Duplicate_CrossInstitution" if is_cross_institution else "Duplicate_IntraApplication"
        })

    return flags
