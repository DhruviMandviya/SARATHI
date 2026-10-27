from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz

def normalize_text_for_comparison(text: str) -> str:
    """Normalizes institution names, removing legal designations and punctuation."""
    if not text:
        return ""
    t = text.lower().strip()
    replacements = [
        ("pvt ltd", ""),
        ("private limited", ""),
        ("limited", ""),
        ("ltd", ""),
        ("trust", ""),
        ("society", ""),
        ("foundation", ""),
        ("campus", ""),
        (".", ""),
        (",", ""),
        ("-", " "),
        ("/", " ")
    ]
    for old, new in replacements:
        t = t.replace(old, new)
    return " ".join(t.split())

def check_consistency(
    declared_details: Dict[str, Any],
    documents_fields: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Compares declared application parameters against values extracted from documents,
    and cross-checks values between different documents.
    Every mismatch flag names BOTH values, BOTH documents, and the similarity score.
    """
    flags: List[Dict[str, Any]] = []

    dec_inst_name = declared_details.get("institution_name", "").strip()
    dec_trust_name = declared_details.get("trust_name", "").strip()
    dec_land_area = declared_details.get("land_area_acres")
    dec_built_up_area = declared_details.get("built_up_area_sqm")

    # 1. Institution Name: Declared vs Extracted in Each Document
    for doc_type, fields in documents_fields.items():
        doc_inst_name = fields.get("institution_name")
        if doc_inst_name and dec_inst_name:
            norm_dec = normalize_text_for_comparison(dec_inst_name)
            norm_doc = normalize_text_for_comparison(doc_inst_name)
            sim_score = fuzz.token_sort_ratio(norm_dec, norm_doc)

            if sim_score < 75.0:
                flags.append({
                    "category": "mismatch",
                    "severity": "critical" if sim_score < 50.0 else "warning",
                    "title": f"Institution Name Mismatch: Declared vs {doc_type.replace('_', ' ').title()}",
                    "explanation": f"Declared name '{dec_inst_name}' does not match extracted name '{doc_inst_name}' in {doc_type.replace('_', ' ').title()} (Similarity: {sim_score:.1f}%).",
                    "evidence": {
                        "declared_value": dec_inst_name,
                        "source_1": "Declared Application Details",
                        "extracted_value": doc_inst_name,
                        "source_2": doc_type,
                        "similarity_score": round(sim_score, 1)
                    },
                    "confidence": round(sim_score / 100.0, 2),
                    "confidence_meaning": "RapidFuzz token-sort ratio text similarity metric",
                    "rule_ref": f"Consistency_InstitutionName_{doc_type}"
                })

    # 2. Institution Name Cross-Document Comparison (e.g. Land Deed vs Fire NOC)
    doc_types = list(documents_fields.keys())
    for i in range(len(doc_types)):
        for j in range(i + 1, len(doc_types)):
            dt1, dt2 = doc_types[i], doc_types[j]
            name1 = documents_fields[dt1].get("institution_name")
            name2 = documents_fields[dt2].get("institution_name")

            if name1 and name2:
                norm1 = normalize_text_for_comparison(name1)
                norm2 = normalize_text_for_comparison(name2)
                sim_score = fuzz.token_sort_ratio(norm1, norm2)

                if sim_score < 75.0:
                    flags.append({
                        "category": "mismatch",
                        "severity": "warning",
                        "title": f"Institution Name Discrepancy: {dt1.replace('_', ' ').title()} vs {dt2.replace('_', ' ').title()}",
                        "explanation": f"Extracted institution name in {dt1.replace('_', ' ').title()} is '{name1}', while in {dt2.replace('_', ' ').title()} it is '{name2}' (Similarity: {sim_score:.1f}%).",
                        "evidence": {
                            "source_1": dt1,
                            "value_1": name1,
                            "source_2": dt2,
                            "value_2": name2,
                            "similarity_score": round(sim_score, 1)
                        },
                        "confidence": round(sim_score / 100.0, 2),
                        "confidence_meaning": "RapidFuzz token-sort ratio cross-document comparison",
                        "rule_ref": f"Consistency_CrossDoc_{dt1}_{dt2}"
                    })

    # 3. Trust Name Comparison
    for doc_type, fields in documents_fields.items():
        doc_trust = fields.get("trust_name")
        if doc_trust and dec_trust_name:
            norm_dec_t = normalize_text_for_comparison(dec_trust_name)
            norm_doc_t = normalize_text_for_comparison(doc_trust)
            sim_score = fuzz.token_sort_ratio(norm_dec_t, norm_doc_t)

            if sim_score < 75.0:
                flags.append({
                    "category": "mismatch",
                    "severity": "warning",
                    "title": f"Trust / Society Name Mismatch: Declared vs {doc_type.replace('_', ' ').title()}",
                    "explanation": f"Declared trust '{dec_trust_name}' does not match extracted trust '{doc_trust}' in {doc_type.replace('_', ' ').title()} (Similarity: {sim_score:.1f}%).",
                    "evidence": {
                        "declared_value": dec_trust_name,
                        "source_1": "Declared Details",
                        "extracted_value": doc_trust,
                        "source_2": doc_type,
                        "similarity_score": round(sim_score, 1)
                    },
                    "confidence": round(sim_score / 100.0, 2),
                    "confidence_meaning": "RapidFuzz fuzzy string matching on promoting body",
                    "rule_ref": f"Consistency_TrustName_{doc_type}"
                })

    # 4. Land Area: Declared vs Land Title Deed Extracted (Numeric with tolerance)
    land_fields = documents_fields.get("land_document", {})
    ext_land_str = land_fields.get("land_area_acres")
    if ext_land_str and dec_land_area is not None:
        try:
            ext_land = float(ext_land_str)
            dec_land = float(dec_land_area)
            diff = abs(dec_land - ext_land)
            # Tolerance: 5% or 0.1 acre
            tolerance = max(dec_land * 0.05, 0.1)

            if diff > tolerance:
                severity = "critical" if dec_land > ext_land * 1.25 else "warning"
                flags.append({
                    "category": "mismatch",
                    "severity": severity,
                    "title": "Land Area Discrepancy: Declared vs Title Deed",
                    "explanation": f"Declared campus land area is {dec_land:.2f} Acres, but extracted area from Land Title Deed is {ext_land:.2f} Acres (Variance: {diff:.2f} Acres exceeds 5% tolerance).",
                    "evidence": {
                        "declared_area_acres": dec_land,
                        "extracted_area_acres": ext_land,
                        "variance_acres": round(diff, 2),
                        "tolerance_allowed": round(tolerance, 2)
                    },
                    "confidence": 1.0,
                    "confidence_meaning": "Deterministic numeric delta check on canonical acreage",
                    "rule_ref": "Consistency_LandArea_Numeric"
                })
        except ValueError:
            pass

    # 5. Built-up Area: Declared vs Building Plan (Numeric with tolerance)
    bp_fields = documents_fields.get("building_plan", {})
    ext_bua_str = bp_fields.get("built_up_area_sqm")
    if ext_bua_str and dec_built_up_area is not None:
        try:
            ext_bua = float(ext_bua_str)
            dec_bua = float(dec_built_up_area)
            diff_bua = abs(dec_bua - ext_bua)
            tol_bua = dec_bua * 0.05

            if diff_bua > tol_bua:
                flags.append({
                    "category": "mismatch",
                    "severity": "warning",
                    "title": "Built-up Area Discrepancy: Declared vs Sanctioned Plan",
                    "explanation": f"Declared built-up area is {dec_bua:.1f} sq.m, but sanctioned plan shows {ext_bua:.1f} sq.m (Variance: {diff_bua:.1f} sq.m).",
                    "evidence": {
                        "declared_bua_sqm": dec_bua,
                        "extracted_bua_sqm": ext_bua,
                        "variance_sqm": round(diff_bua, 1)
                    },
                    "confidence": 1.0,
                    "confidence_meaning": "Deterministic numeric comparison between declared and municipal sanctioned area",
                    "rule_ref": "Consistency_BuiltUpArea_Numeric"
                })
        except ValueError:
            pass

    # 6. Date Chronology Logic (e.g. issue_date before validity_date)
    for doc_type, fields in documents_fields.items():
        issue_d = fields.get("issue_date")
        val_d = fields.get("validity_date")
        if issue_d and val_d:
            try:
                from datetime import datetime
                d_issue = datetime.strptime(issue_d, "%Y-%m-%d")
                d_val = datetime.strptime(val_d, "%Y-%m-%d")
                if d_issue > d_val:
                    flags.append({
                        "category": "mismatch",
                        "severity": "critical",
                        "title": f"Chronological Inconsistency in {doc_type.replace('_', ' ').title()}",
                        "explanation": f"Issue date ({issue_d}) is chronologically after the validity/expiry date ({val_d}).",
                        "evidence": {"issue_date": issue_d, "validity_date": val_d, "doc_type": doc_type},
                        "confidence": 1.0,
                        "confidence_meaning": "Deterministic date order comparison",
                        "rule_ref": f"Consistency_DateOrder_{doc_type}"
                    })
            except Exception:
                pass

    return flags
