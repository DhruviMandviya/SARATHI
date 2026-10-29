from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.application import Application
from backend.app.models.finding import Flag
from backend.app.models.compliance import ComplianceResult, ComplianceRule
from backend.app.models.verification import VerificationResult
from backend.app.models.document import Document

class RiskEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_application_risk(self, application_id: int) -> Dict[str, Any]:
        """
        Calculates an explainable Review-Priority Score capped at 100.
        Crucial requirement: Score measures scrutiny priority, NEVER fraud probability or guilt.
        """
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        factors: List[Dict[str, Any]] = []
        raw_score = 0

        # 1. Inspect Flags (open and acknowledged) - robust deduplication by normalized issue key
        raw_flags = self.db.query(Flag).filter(
            Flag.application_id == application_id,
            Flag.status.in_(["open", "acknowledged"])
        ).all()

        seen_flag_keys = set()
        flags = []
        for f in raw_flags:
            if f.category == "duplicate":
                matched_id = (f.evidence or {}).get("matched_doc_id") or f.related_document_id or 0
                doc_a, doc_b = sorted([f.document_id or 0, matched_id])
                key = ("duplicate", doc_a, doc_b)
            elif f.category in ("tampering", "metadata"):
                # Group repeated forensic signals per document to avoid multi-detector inflation
                key = (f.category, f.document_id, f.title.split("(")[0].strip())
            else:
                key = (f.category, f.document_id, f.title)

            if key not in seen_flag_keys:
                seen_flag_keys.add(key)
                flags.append(f)

        crit_count = 0
        warn_count = 0
        info_count = 0
        duplicate_pts_total = 0

        for f in flags:
            # AICTE standard template layout matches are expected forms, not risk points
            is_template = (
                f.rule_ref == "Duplicate_TemplateAware" or
                "standard statutory template" in f.title.lower() or
                "standard template" in f.title.lower()
            )

            if is_template:
                pts = 0
            elif f.severity == "critical":
                pts = 25
                crit_count += 1
            elif f.severity == "warning":
                pts = 10
                warn_count += 1
            else:
                pts = 2
                info_count += 1

            # Cap intra-application duplicate contribution so repeated files don't blow up score
            if f.category == "duplicate" and f.severity != "critical":
                if duplicate_pts_total >= 30:
                    pts = 0
                else:
                    pts = min(pts, 30 - duplicate_pts_total)
                    duplicate_pts_total += pts

            if pts > 0 or is_template:
                raw_score += pts
                factors.append({
                    "source": "Document Finding",
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.explanation[:120] + ("..." if len(f.explanation) > 120 else ""),
                    "points": pts
                })

        # 2. Inspect Compliance Deficiencies
        comp_results = self.db.query(ComplianceResult).filter(
            ComplianceResult.application_id == application_id
        ).all()

        comp_deficits = 0
        for cr in comp_results:
            if cr.outcome == "non_compliant":
                pts = 15
                comp_deficits += 1
                raw_score += pts
                rule = self.db.query(ComplianceRule).filter(ComplianceRule.id == cr.rule_id).first()
                rule_name = rule.name if rule else f"Rule #{cr.rule_id}"
                factors.append({
                    "source": "Regulatory Non-Compliance",
                    "severity": "warning",
                    "title": f"Non-Compliant: {rule_name}",
                    "detail": cr.explanation[:120] + ("..." if len(cr.explanation) > 120 else ""),
                    "points": pts
                })

        # 3. Inspect Authenticity Verification Failures
        docs = self.db.query(Document).filter(
            Document.application_id == application_id,
            Document.superseded_by.is_(None)
        ).all()
        doc_ids = [d.id for d in docs]

        ver_results = self.db.query(VerificationResult).filter(
            VerificationResult.document_id.in_(doc_ids)
        ).all() if doc_ids else []

        auth_discrepancies = 0
        for vr in ver_results:
            if vr.status == "not_verified":
                pts = 20
                auth_discrepancies += 1
                raw_score += pts
                factors.append({
                    "source": "External Authority Verification",
                    "severity": "critical",
                    "title": f"Registry Discrepancy: {vr.authority}",
                    "detail": vr.message or "Reference not found in authority repository.",
                    "points": pts
                })

        # Cap score between 0 and 100
        score = min(100, max(0, raw_score))

        # Determine review priority band
        if score >= 60:
            band = "High"
        elif score >= 25:
            band = "Medium"
        else:
            band = "Low"

        # Sort factors by points descending
        factors.sort(key=lambda x: x["points"], reverse=True)
        top_factors = factors[:5]

        breakdown = {
            "score": score,
            "band": band,
            "raw_calculated_score": raw_score,
            "critical_flags_count": crit_count,
            "warning_flags_count": warn_count,
            "info_flags_count": info_count,
            "compliance_deficits_count": comp_deficits,
            "authority_discrepancies_count": auth_discrepancies,
            "top_contributing_factors": top_factors,
            "philosophy_disclaimer": "Review Priority Score indicates recommended official scrutiny urgency. The AI recommends; the authorised official decides."
        }

        # Persist to application record
        app.risk_score = score
        app.risk_band = band
        app.risk_breakdown = breakdown
        self.db.commit()
        self.db.refresh(app)

        return breakdown
