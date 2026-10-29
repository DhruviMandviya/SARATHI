import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.compliance import ComplianceRule, ComplianceResult
from backend.app.models.application import Application
from backend.app.models.document import Document

class ComplianceEngine:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_application(self, application_id: int) -> List[ComplianceResult]:
        """
        Evaluates all active compliance rules against an application's declared details
        and extracted document data.
        Saves and returns the evaluated ComplianceResult records.
        """
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        # Aggregate application context from declared details and extracted documents
        context = self._build_evaluation_context(app)

        # Fetch all active compliance rules
        active_rules = self.db.query(ComplianceRule).filter(ComplianceRule.active == True).all()

        # Remove existing results for this application to avoid duplicate stale rows
        self.db.query(ComplianceResult).filter(ComplianceResult.application_id == application_id).delete()

        results = []
        for rule in active_rules:
            result = self._evaluate_rule(rule, context, application_id)
            self.db.add(result)
            results.append(result)

        self.db.commit()
        for r in results:
            self.db.refresh(r)
        return results

    def _build_evaluation_context(self, app: Application) -> Dict[str, Any]:
        """
        Combines declared details and all successfully extracted document fields into a unified lookup.
        Extracted document fields take precedence or supplement declared details.
        """
        ctx: Dict[str, Any] = {}
        if app.declared_details and isinstance(app.declared_details, dict):
            ctx.update(app.declared_details)

        # Merge extracted fields from completed documents
        for doc in app.documents:
            if doc.extracted_data and isinstance(doc.extracted_data, dict):
                # Put document type specific keys
                for k, v in doc.extracted_data.items():
                    if v is not None and v != "":
                        ctx[k] = v

        return ctx

    def _evaluate_rule(self, rule: ComplianceRule, context: Dict[str, Any], application_id: int) -> ComplianceResult:
        params = rule.parameters or {}
        field = params.get("field")
        val = context.get(field)

        # Check for missing data
        if val is None or val == "":
            outcome = rule.on_missing_data or "needs_review"
            req_str = self._format_requirement(rule, params)
            prov_str = "Not provided / Not detected in documents"
            explanation = (
                f"Required parameter '{field}' was not found in declared institutional details or extracted document fields. "
                f"Action marked as '{outcome}' per policy."
            )
            return ComplianceResult(
                application_id=application_id,
                rule_id=rule.id,
                rule_version=rule.version,
                required_value=req_str,
                provided_value=prov_str,
                outcome=outcome,
                explanation=explanation
            )

        # Evaluate based on check_type
        if rule.check_type == "min_value":
            return self._evaluate_min_value(rule, params, val, application_id)
        elif rule.check_type == "ratio_max":
            return self._evaluate_ratio_max(rule, params, val, application_id)
        elif rule.check_type == "boolean_present":
            return self._evaluate_boolean_present(rule, params, val, application_id)
        elif rule.check_type == "enum_match":
            return self._evaluate_enum_match(rule, params, val, application_id)
        else:
            return ComplianceResult(
                application_id=application_id,
                rule_id=rule.id,
                rule_version=rule.version,
                required_value=str(params),
                provided_value=str(val),
                outcome="needs_review",
                explanation=f"Unsupported check type: {rule.check_type}"
            )

    def _evaluate_min_value(self, rule: ComplianceRule, params: Dict[str, Any], raw_val: Any, application_id: int) -> ComplianceResult:
        min_required = float(params.get("min_value", 0))
        unit = params.get("unit", "")
        req_str = f"Minimum {min_required} {unit}".strip()

        # Parse numeric value
        num_val = self._parse_numeric(raw_val)
        if num_val is None:
            return ComplianceResult(
                application_id=application_id,
                rule_id=rule.id,
                rule_version=rule.version,
                required_value=req_str,
                provided_value=str(raw_val),
                outcome=rule.on_missing_data or "needs_review",
                explanation=f"Value '{raw_val}' could not be parsed as a numeric quantity for comparison with required minimum of {min_required} {unit}."
            )

        prov_str = f"{num_val} {unit}".strip()

        if num_val >= min_required:
            outcome = "compliant"
            explanation = (
                f"Meets regulatory requirement: {num_val} {unit} satisfies the minimum required threshold of {min_required} {unit} "
                f"under {rule.clause} ({rule.source})."
            )
        else:
            outcome = "non_compliant"
            deficit = round(min_required - num_val, 2)
            explanation = (
                f"Deficiency detected: Provided {num_val} {unit} is below the mandatory minimum of {min_required} {unit} "
                f"(Deficit: {deficit} {unit}) under {rule.clause} ({rule.source})."
            )

        if not rule.verified_against_handbook:
            explanation += " [Note: Evaluation evaluated against unverified draft threshold pending official AICTE handbook gazette confirmation.]"

        return ComplianceResult(
            application_id=application_id,
            rule_id=rule.id,
            rule_version=rule.version,
            required_value=req_str,
            provided_value=prov_str,
            outcome=outcome,
            explanation=explanation
        )

    def _evaluate_ratio_max(self, rule: ComplianceRule, params: Dict[str, Any], raw_val: Any, application_id: int) -> ComplianceResult:
        max_ratio = float(params.get("max_ratio", 20.0))
        std_str = params.get("standard", f"1:{max_ratio}")
        req_str = f"Maximum ratio {std_str} (<= {max_ratio})"

        # Raw value might be a float like 18.5 or string "1:18"
        num_val = self._parse_ratio(raw_val)
        if num_val is None:
            return ComplianceResult(
                application_id=application_id,
                rule_id=rule.id,
                rule_version=rule.version,
                required_value=req_str,
                provided_value=str(raw_val),
                outcome=rule.on_missing_data or "needs_review",
                explanation=f"Cadre ratio '{raw_val}' could not be parsed to numeric comparison format."
            )

        prov_str = f"1:{num_val}"
        if num_val <= max_ratio:
            outcome = "compliant"
            explanation = (
                f"Compliant: Faculty cadre ratio 1:{num_val} satisfies maximum permissible ratio of {std_str} "
                f"pursuant to {rule.clause}."
            )
        else:
            outcome = "non_compliant"
            explanation = (
                f"Non-compliant: Student-faculty ratio 1:{num_val} exceeds maximum allowed ratio of {std_str} "
                f"under {rule.clause}."
            )

        if not rule.verified_against_handbook:
            explanation += " [Note: Evaluated against unverified draft ratio pending official AICTE handbook confirmation.]"

        return ComplianceResult(
            application_id=application_id,
            rule_id=rule.id,
            rule_version=rule.version,
            required_value=req_str,
            provided_value=prov_str,
            outcome=outcome,
            explanation=explanation
        )

    def _evaluate_boolean_present(self, rule: ComplianceRule, params: Dict[str, Any], raw_val: Any, application_id: int) -> ComplianceResult:
        req_str = "Required / Mandatory"
        is_true = raw_val is True or str(raw_val).lower() in ("true", "yes", "present", "1")
        prov_str = "Present" if is_true else "Absent / False"

        outcome = "compliant" if is_true else "non_compliant"
        explanation = (
            f"Requirement {'satisfied' if is_true else 'not satisfied'}: {rule.name} "
            f"under {rule.clause}."
        )

        return ComplianceResult(
            application_id=application_id,
            rule_id=rule.id,
            rule_version=rule.version,
            required_value=req_str,
            provided_value=prov_str,
            outcome=outcome,
            explanation=explanation
        )

    def _evaluate_enum_match(self, rule: ComplianceRule, params: Dict[str, Any], raw_val: Any, application_id: int) -> ComplianceResult:
        allowed = [str(x).lower() for x in params.get("allowed_values", [])]
        req_str = f"One of: {', '.join(params.get('allowed_values', []))}"
        prov_str = str(raw_val)

        is_match = str(raw_val).strip().lower() in allowed
        outcome = "compliant" if is_match else "non_compliant"
        explanation = (
            f"Classification '{raw_val}' {'matches' if is_match else 'does not match'} required categories "
            f"specified in {rule.clause}."
        )

        return ComplianceResult(
            application_id=application_id,
            rule_id=rule.id,
            rule_version=rule.version,
            required_value=req_str,
            provided_value=prov_str,
            outcome=outcome,
            explanation=explanation
        )

    def _format_requirement(self, rule: ComplianceRule, params: Dict[str, Any]) -> str:
        if rule.check_type == "min_value":
            return f"Minimum {params.get('min_value')} {params.get('unit', '')}".strip()
        elif rule.check_type == "ratio_max":
            return f"Maximum ratio {params.get('standard', '')}".strip()
        elif rule.check_type == "boolean_present":
            return "Mandatory Affirmation / Present"
        elif rule.check_type == "enum_match":
            return f"Must match {params.get('allowed_values')}"
        return str(params)

    def _parse_numeric(self, val: Any) -> Optional[float]:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace(",", "")
        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
        return None

    def _parse_ratio(self, val: Any) -> Optional[float]:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if ":" in s:
            parts = s.split(":")
            try:
                denom = float(parts[1].strip())
                return denom
            except (ValueError, IndexError):
                pass
        return self._parse_numeric(val)
