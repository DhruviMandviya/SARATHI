from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.application import Application
from backend.app.models.finding import Flag
from backend.app.models.compliance import ComplianceResult, ComplianceRule
from backend.app.models.verification import VerificationResult
from backend.app.models.document import Document

# Actionability constants
INTERNAL_REVIEW_ONLY = "INTERNAL_REVIEW_ONLY"
APPLICANT_CLARIFICATION_REQUIRED = "APPLICANT_CLARIFICATION_REQUIRED"
DOCUMENT_REPLACEMENT_REQUIRED = "DOCUMENT_REPLACEMENT_REQUIRED"
MANDATORY_DOCUMENT_MISSING = "MANDATORY_DOCUMENT_MISSING"
AUTHORITY_VERIFICATION_PENDING = "AUTHORITY_VERIFICATION_PENDING"
RESOLVED = "RESOLVED"
DISMISSED_WITH_REASON = "DISMISSED_WITH_REASON"

MANDATORY_CHECKLIST_DOC_TYPES = [
    "land_document",
    "building_plan",
    "fire_noc",
    "society_registration",
    "affidavit"
]

def classify_flag(flag: Flag) -> Dict[str, Any]:
    """
    Classifies a single Flag into its regulatory scrutiny group,
    actionability status, and applicant-facing suitability.
    Crucial regulatory principle: Internal forensic signals and duplicate detections
    are for official review and must NOT automatically become applicant deficiencies.
    """
    cat = (flag.category or "").lower()
    title_lower = (flag.title or "").lower()

    if cat == "duplicate":
        group = "duplicate_similarity"
        actionability = INTERNAL_REVIEW_ONLY
        is_actionable = False
        default_req_action = "Official Scrutiny Committee review of potential document similarity."
    elif cat in ("tampering", "metadata"):
        group = "internal_forensics"
        actionability = INTERNAL_REVIEW_ONLY
        is_actionable = False
        default_req_action = "Official forensic signal inspection (ELA / metadata heuristic analysis)."
    elif cat == "verification":
        group = "authority_pending"
        actionability = AUTHORITY_VERIFICATION_PENDING
        is_actionable = False
        default_req_action = "Pending statutory verification check against external simulated registry."
    elif cat in ("mismatch", "consistency"):
        group = "material_inconsistencies"
        actionability = APPLICANT_CLARIFICATION_REQUIRED
        is_actionable = True
        default_req_action = "Submit written clarification and certified supporting documents reconciling the identified inconsistency."
    elif cat in ("missing", "expired"):
        group = "mandatory_compliance"
        actionability = MANDATORY_DOCUMENT_MISSING if cat == "missing" else DOCUMENT_REPLACEMENT_REQUIRED
        is_actionable = True
        default_req_action = "Upload current, valid, certified statutory document conforming to AICTE norms."
    elif cat == "incomplete" or "incomplete" in title_lower or "single-page" in title_lower:
        group = "document_clarifications"
        actionability = DOCUMENT_REPLACEMENT_REQUIRED
        is_actionable = True
        default_req_action = "Upload complete scan including all registered schedules, boundaries, and attestation pages."
    else:
        # Quality or other general checks
        if flag.severity == "critical":
            group = "material_inconsistencies"
            actionability = APPLICANT_CLARIFICATION_REQUIRED
            is_actionable = True
            default_req_action = "Provide clarifying explanation and supporting institutional records."
        else:
            group = "document_clarifications"
            actionability = INTERNAL_REVIEW_ONLY
            is_actionable = False
            default_req_action = "Review scan quality and legibility."

    doc_type = "general_compliance"
    doc_name = "Statutory Document"
    doc = getattr(flag, "document", None)
    if doc:
        doc_type = getattr(doc, "doc_type", doc_type) or doc_type
        doc_name = getattr(doc, "original_filename", doc_name) or doc_name
    elif getattr(flag, "evidence", None) and isinstance(flag.evidence, dict) and flag.evidence.get("doc_type"):
        doc_type = flag.evidence.get("doc_type")
        doc_name = flag.evidence.get("document_name", doc_name)

    return {
        "finding_id": getattr(flag, "id", None),
        "group": group,
        "candidate_category": group,
        "actionability": actionability,
        "is_actionable": is_actionable,
        "category": getattr(flag, "category", None),
        "severity": getattr(flag, "severity", None),
        "title": getattr(flag, "title", None),
        "doc_type": doc_type,
        "document_name": doc_name,
        "explanation": getattr(flag, "explanation", None),
        "rule_ref": getattr(flag, "rule_ref", None) or "AICTE_APH_Norms",
        "default_requested_action": default_req_action,
        "requires_explanation": True,
        "requires_upload": (actionability in (DOCUMENT_REPLACEMENT_REQUIRED, MANDATORY_DOCUMENT_MISSING)),
        "status": getattr(flag, "status", "open")
    }

def get_candidate_notice_items(application_id: int, db: Session) -> Dict[str, Any]:
    """
    Gathers all candidate findings for an application and groups them into:
    - mandatory_compliance (Actionable candidate)
    - material_inconsistencies (Actionable candidate)
    - document_clarifications (Actionable candidate)
    - internal_forensics (Internal review only - NOT pre-selected)
    - duplicate_similarity (Internal review only - NOT pre-selected)
    - authority_pending (Internal review only - NOT pre-selected)
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application {application_id} not found")

    # 1. Inspect open / acknowledged flags
    flags = db.query(Flag).filter(
        Flag.application_id == application_id,
        Flag.status.in_(["open", "acknowledged"])
    ).all()

    # Deduplicate flags by normalized pair / category so duplicate alerts don't multiply candidates
    seen_keys = set()
    deduped_flags = []
    for f in flags:
        if f.category == "duplicate":
            matched_id = (f.evidence or {}).get("matched_doc_id") or f.related_document_id or 0
            doc_a, doc_b = sorted([f.document_id or 0, matched_id])
            key = ("duplicate", doc_a, doc_b)
        else:
            key = (f.category, f.document_id, f.title.strip())

        if key not in seen_keys:
            seen_keys.add(key)
            deduped_flags.append(f)

    # 2. Inspect compliance deficits
    comp_results = db.query(ComplianceResult).filter(
        ComplianceResult.application_id == application_id,
        ComplianceResult.outcome.in_(["non_compliant", "needs_review"])
    ).all()

    # 3. Categorize candidates
    groups = {
        "mandatory_compliance": [],
        "material_inconsistencies": [],
        "document_clarifications": [],
        "internal_forensics": [],
        "duplicate_similarity": [],
        "authority_pending": []
    }

    item_idx = 1
    for f in deduped_flags:
        cf = classify_flag(f)
        candidate_item = {
            "id": f"cand-{item_idx}",
            "finding_id": f.id,
            "group": cf["group"],
            "category": cf["category"],
            "severity": cf["severity"],
            "actionability": cf["actionability"],
            "is_actionable": cf["is_actionable"],
            "title": cf["title"],
            "doc_type": cf["doc_type"],
            "document_name": cf["document_name"],
            "explanation": cf["explanation"],
            "rule_ref": cf["rule_ref"],
            "requested_action": cf["default_requested_action"],
            "requires_explanation": cf["requires_explanation"],
            "requires_upload": cf["requires_upload"],
            "status": cf["status"]
        }
        item_idx += 1
        groups[cf["group"]].append(candidate_item)

    # Add regulatory compliance deficits as mandatory compliance candidates
    for cr in comp_results:
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == cr.rule_id).first()
        r_name = rule.name if rule else f"Rule #{cr.rule_id}"
        clause = rule.clause if rule else "APH Clause"
        doc_type = rule.document_type if rule and rule.document_type else "general_compliance"

        groups["mandatory_compliance"].append({
            "id": f"cand-{item_idx}",
            "finding_id": None,
            "group": "mandatory_compliance",
            "category": "compliance",
            "severity": "critical" if cr.outcome == "non_compliant" else "warning",
            "actionability": MANDATORY_DOCUMENT_MISSING if "missing" in r_name.lower() else APPLICANT_CLARIFICATION_REQUIRED,
            "is_actionable": True,
            "title": f"Regulatory Deficit: {r_name}",
            "doc_type": doc_type,
            "document_name": f"{doc_type.replace('_', ' ').title()}",
            "explanation": cr.explanation,
            "rule_ref": f"{r_name} ({clause})",
            "requested_action": f"Remedy non-compliance with {clause} and provide supporting institutional verification.",
            "requires_explanation": True,
            "requires_upload": True,
            "status": "open"
        })
        item_idx += 1

    total_candidates = sum(len(items) for items in groups.values())
    actionable_count = len(groups["mandatory_compliance"]) + len(groups["material_inconsistencies"]) + len(groups["document_clarifications"])
    internal_only_count = len(groups["internal_forensics"]) + len(groups["duplicate_similarity"]) + len(groups["authority_pending"])

    return {
        "application_id": app.id,
        "application_no": app.application_no,
        "academic_year": app.academic_year,
        "institution_name": app.institution.name if app.institution else "Applicant Institution",
        "groups": groups,
        "summary": {
            "total_candidates": total_candidates,
            "actionable_count": actionable_count,
            "internal_only_count": internal_only_count
        }
    }
