from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.application import Application
from backend.app.models.decision import Decision, DeficiencyLetter
from backend.app.models.finding import Flag
from backend.app.models.compliance import ComplianceResult, ComplianceRule
from backend.app.models.information_request import InformationRequest
from backend.app.services.deficiency_letter import generate_deficiency_letter_text
from backend.app.services.notification import notify_institution
from backend.app.services.audit import record_audit_event

def persist_official_notice_for_application(
    app: Application,
    official_id: int,
    remarks: str,
    db: Session,
    custom_letter_text: Optional[str] = None,
    deadline_days: int = 15
) -> InformationRequest:
    """
    Persists an authoritative, formal Information Request / Deficiency Notice
    when an official issues an 'info_requested' decision.
    Ensures idempotency (no duplicate notices on retry).
    """
    ref_no = f"AICTE/RO/SCRUTINY/{app.academic_year}/{app.application_no}/DEF-01"
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=deadline_days)

    # 1. Gather deficiency items from flags and compliance deficits
    flags = db.query(Flag).filter(
        Flag.application_id == app.id,
        Flag.status.in_(["open", "acknowledged"])
    ).all()

    comp_results = db.query(ComplianceResult).filter(
        ComplianceResult.application_id == app.id,
        ComplianceResult.outcome.in_(["non_compliant", "needs_review"])
    ).all()

    from backend.app.services.finding_classification import classify_flag

    def_items: List[Dict[str, Any]] = []
    item_counter = 1

    # Map only actionable flags to deficiency items (exclude internal forensics, duplicates, pending authority checks)
    seen_flag_keys = set()
    for f in flags:
        cf = classify_flag(f)
        if not cf["is_actionable"]:
            continue
        key = (cf["category"], f.document_id, cf["title"].strip())
        if key in seen_flag_keys:
            continue
        seen_flag_keys.add(key)

        def_items.append({
            "id": f"def-{item_counter}",
            "finding_id": f.id,
            "category": cf["group"],
            "doc_type": cf["doc_type"],
            "requirement": f.title,
            "explanation": f.explanation,
            "requested_action": cf["default_requested_action"],
            "requires_explanation": cf["requires_explanation"],
            "requires_upload": cf["requires_upload"],
            "mandatory": True,
            "response_status": "pending",
            "official_review_status": "pending"
        })
        item_counter += 1

    # Map compliance results to deficiency items
    for cr in comp_results:
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == cr.rule_id).first()
        r_name = rule.name if rule else f"Rule #{cr.rule_id}"
        clause = getattr(rule, "clause", "APH Clause") or "APH Clause"
        doc_type = getattr(rule, "document_type", "regulatory_compliance") or "regulatory_compliance"
        def_items.append({
            "id": f"def-{item_counter}",
            "finding_id": None,
            "category": "mandatory_compliance",
            "doc_type": doc_type,
            "requirement": r_name,
            "explanation": cr.explanation,
            "requested_action": f"Provide compliance explanation and rectifying certified documentation under {clause}.",
            "requires_explanation": True,
            "requires_upload": True,
            "mandatory": True,
            "response_status": "pending",
            "official_review_status": "pending"
        })
        item_counter += 1

    # Determine doc_type from official remarks if relevant
    lower_rem = remarks.lower()
    rem_doc_type = "general_compliance"
    if "land" in lower_rem or "survey" in lower_rem or "acres" in lower_rem:
        rem_doc_type = "land_document"
    elif "fire" in lower_rem or "noc" in lower_rem:
        rem_doc_type = "fire_noc"
    elif "building" in lower_rem or "sqm" in lower_rem or "built" in lower_rem:
        rem_doc_type = "building_plan"
    elif "society" in lower_rem or "trust" in lower_rem or "reg" in lower_rem:
        rem_doc_type = "society_registration"
    elif "affidavit" in lower_rem:
        rem_doc_type = "affidavit"

    # Always ensure the specific official directive from remarks is captured
    def_items.append({
        "id": "def-dir-1",
        "doc_type": rem_doc_type,
        "requirement": "Statutory Rectification Directive",
        "explanation": remarks,
        "mandatory": True
    })

    # 2. Get notice letter text
    if custom_letter_text and custom_letter_text.strip():
        letter_text = custom_letter_text.strip()
    else:
        # Check if an edited draft was saved
        def_letter = db.query(DeficiencyLetter).filter(
            DeficiencyLetter.application_id == app.id
        ).first()
        if def_letter and def_letter.edited_text:
            letter_text = def_letter.edited_text
        else:
            letter_data = generate_deficiency_letter_text(app.id, db)
            letter_text = letter_data.get("letter_text", remarks)

    # 3. Check for existing InformationRequest on this application (idempotency)
    existing_req = db.query(InformationRequest).filter(
        InformationRequest.application_id == app.id
    ).order_by(desc(InformationRequest.id)).first()

    if existing_req:
        existing_req.reference_no = ref_no
        existing_req.title = f"Scrutiny Deficiency Notice regarding Application for Approval ({app.academic_year})"
        existing_req.reason = remarks
        existing_req.notice_text = letter_text
        existing_req.status = "action_required"
        existing_req.deficiencies = def_items
        existing_req.issued_by = official_id
        existing_req.issued_at = now
        existing_req.deadline = deadline
        existing_req.updated_at = now
        req = existing_req
    else:
        req = InformationRequest(
            reference_no=ref_no,
            application_id=app.id,
            institution_id=app.institution_id,
            title=f"Scrutiny Deficiency Notice regarding Application for Approval ({app.academic_year})",
            reason=remarks,
            notice_text=letter_text,
            status="action_required",
            issuing_authority="AICTE Scrutiny Committee",
            issued_by=official_id,
            issued_at=now,
            deadline=deadline,
            deficiencies=def_items,
            created_at=now
        )
        db.add(req)

    # 4. Sync DeficiencyLetter model
    letter_record = db.query(DeficiencyLetter).filter(
        DeficiencyLetter.application_id == app.id
    ).first()
    if letter_record:
        letter_record.edited_text = letter_text
        letter_record.status = "sent"
        letter_record.updated_at = now
    else:
        letter_record = DeficiencyLetter(
            application_id=app.id,
            draft_text=letter_text,
            edited_text=letter_text,
            status="sent",
            created_by=official_id,
            created_at=now,
            updated_at=now
        )
        db.add(letter_record)

    # 5. Notify institution with link to Information Requests page
    notify_institution(
        db=db,
        institution_id=app.institution_id,
        title=f"Statutory Notice Issued: {ref_no}",
        message=f"Formal Deficiency Notice {ref_no} has been issued for application {app.application_no}. Response deadline: {deadline.strftime('%d %B %Y')}. Action required.",
        category="notice_issued",
        application_id=app.id,
        link=f"/information-requests/{req.id if req.id else ''}",
        reference_id=ref_no
    )

    from backend.app.models.user import User
    official_actor = db.query(User).filter(User.id == official_id).first()
    if not official_actor:
        official_actor = db.query(User).filter(User.role == "official").first()

    record_audit_event(
        db=db,
        action="ISSUE_DEFICIENCY_NOTICE",
        entity_type="information_request",
        entity_id=app.id,
        actor=official_actor,
        before_state={"status": app.status},
        after_state={"reference_no": ref_no, "status": "action_required", "deadline": str(deadline)}
    )

    return req

def sync_unpersisted_info_requested_notices(db: Session):
    """
    Backfill helper: Checks all applications in 'info_requested' status.
    If an application has an official decision of info_requested but lacks an
    issued InformationRequest, persist one so it appears authoritatively on the portal.
    """
    try:
        from sqlalchemy import text
        res = db.execute(text("PRAGMA table_info(information_requests);")).fetchall()
        cols = [r[1] for r in res]
        if cols and "reason" not in cols:
            db.execute(text("ALTER TABLE information_requests ADD COLUMN reason TEXT DEFAULT '' NOT NULL;"))
            db.commit()
    except Exception:
        db.rollback()

    apps = db.query(Application).filter(Application.status == "info_requested").all()
    for app in apps:
        existing_req = db.query(InformationRequest).filter(
            InformationRequest.application_id == app.id
        ).first()

        if not existing_req:
            # Find the recorded decision
            dec = db.query(Decision).filter(
                Decision.application_id == app.id,
                Decision.outcome == "info_requested"
            ).first()

            official_id = dec.official_id if dec else 3
            remarks = dec.remarks if dec else "Document clarification and regulatory cure required by Scrutiny Committee."

            try:
                persist_official_notice_for_application(
                    app=app,
                    official_id=official_id,
                    remarks=remarks,
                    db=db
                )
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[SYNC_NOTICE_ERROR] Could not sync notice for App {app.id}: {e}")
