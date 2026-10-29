from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models.application import Application
from backend.app.models.finding import Flag
from backend.app.models.compliance import ComplianceResult, ComplianceRule

def generate_deficiency_letter_text(application_id: int, db: Session) -> Dict[str, Any]:
    """
    Generates a formal, structured draft deficiency letter based on real application findings,
    missing mandatory documents, expired certificates, and compliance deficits.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application {application_id} not found")

    inst_name = app.institution.name if app.institution else "The Applicant Institution"
    inst_addr = app.institution.address if app.institution else "Institutional Campus"
    inst_aicte_id = app.institution.aicte_id if app.institution else "TEMP-ID"

    # Gather open deficiency flags
    flags = db.query(Flag).filter(
        Flag.application_id == application_id,
        Flag.status.in_(["open", "acknowledged"])
    ).all()

    # Gather compliance failures
    comp_results = db.query(ComplianceResult).filter(
        ComplianceResult.application_id == application_id,
        ComplianceResult.outcome.in_(["non_compliant", "needs_review"])
    ).all()

    deficiency_items: List[str] = []

    from backend.app.services.finding_classification import classify_flag

    # 1. Actionable Flag items only (exclude internal forensics, duplicates, and authority pending)
    seen_flag_keys = set()
    for f in flags:
        cf = classify_flag(f)
        if not cf["is_actionable"]:
            continue
        key = (cf["category"], f.document_id, cf["title"].strip())
        if key in seen_flag_keys:
            continue
        seen_flag_keys.add(key)
        deficiency_items.append(f"[{f.severity.upper()}] {f.title}: {f.explanation}")

    # 2. Compliance deficits
    for cr in comp_results:
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == cr.rule_id).first()
        r_name = rule.name if rule else f"Rule #{cr.rule_id}"
        deficiency_items.append(f"[REGULATORY DEFICIT] {r_name} (Clause: {rule.clause if rule else 'APH'}): {cr.explanation}")

    if not deficiency_items:
        deficiency_items.append("No specific statutory deficiencies or document defects were identified during automated preliminary scrutiny.")

    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    cure_deadline = (datetime.now(timezone.utc) + timedelta(days=15)).strftime("%d %B %Y")
    ref_no = f"AICTE/RO/SCRUTINY/{app.academic_year}/{app.application_no}/DEF-01"

    numbered_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(deficiency_items)])

    letter_body = f"""ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
(A Statutory Body Under Ministry of Education, Govt. of India)
Regional Office — Technical Scrutiny & Approval Division

Ref No: {ref_no}
Date: {date_str}

To,
The Chairman / Secretary / Principal,
{inst_name}
{inst_addr}
AICTE Permanent / Application ID: {inst_aicte_id}

SUBJECT: Scrutiny Deficiency Notice regarding Application for Approval ({app.academic_year}) — Reg.

Sir / Madam,

This has reference to your Application No. {app.application_no} submitted for {app.type.replace('_', ' ').title()} for the Academic Year {app.academic_year}.

On preliminary verification and automated regulatory scrutiny of the documents uploaded in support of your application, the following deficiencies, discrepancies, and incomplete records have been noted:

{numbered_list}

In terms of the provisions of the AICTE Approval Process Handbook (APH), you are hereby directed to rectify the above-mentioned deficiencies and submit your compliance explanation, along with certified documentary evidence, on the SARATHI AICTE Portal within fifteen (15) days of the date of this notice, i.e., on or before {cure_deadline}.

Please note that failure to rectify the deficiencies within the stipulated period may result in an adverse recommendation by the Scrutiny Committee for the grant of approval for the Academic Year {app.academic_year}.

This issues with the approval of the Competent Authority.

Yours faithfully,

Member Secretary / Regional Officer
AICTE Regional Scrutiny Cell
"""

    return {
        "application_id": app.id,
        "application_no": app.application_no,
        "reference_no": ref_no,
        "generated_date": date_str,
        "cure_deadline": cure_deadline,
        "deficiency_count": len(deficiency_items),
        "deficiencies": deficiency_items,
        "letter_text": letter_body.strip()
    }
