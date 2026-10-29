from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome

class LandRecordsVerifier(BaseVerifier):
    authority_name = "State Land & Revenue Department (Sub-Registrar Land Records)"
    adapter_name = "mock_state_land_records_adapter"

    def verify(
        self,
        reference_no: Optional[str],
        document_context: Optional[Dict[str, Any]] = None
    ) -> VerificationOutcome:
        context = document_context or {}
        ref = (
            reference_no or
            context.get("deed_number") or
            context.get("survey_number") or
            ""
        ).strip()

        if not ref:
            return VerificationOutcome(
                status="pending",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=None,
                is_simulated=True,
                message="No land deed registration or survey reference number detected in extracted data. Pending manual verification.",
                raw_response={"simulated_gateway": "offline", "reason": "missing_ref_number"}
            )

        ref_upper = ref.upper()

        if ref_upper.endswith("PEND") or ref_upper.endswith("99"):
            return VerificationOutcome(
                status="pending",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="State Land Revenue portal gateway timed out. Marked Pending Verification.",
                raw_response={"simulated_code": 504, "endpoint": "https://landrecords.gov.in/api/v1/verify"}
            )

        if ref_upper.endswith("REJ") or ref_upper.endswith("00"):
            return VerificationOutcome(
                status="not_verified",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Title deed registration and survey plot not found in state revenue records.",
                raw_response={"simulated_code": 404, "record_found": False}
            )

        if ref_upper.endswith("PROG"):
            return VerificationOutcome(
                status="in_progress",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Tehsildar land parcel boundary demarcating inspection scheduled.",
                raw_response={"simulated_code": 202, "status": "INSPECTION_SCHEDULED"}
            )

        survey = context.get("survey_number") or ref
        acres = context.get("land_area_acres") or "3.5"
        return VerificationOutcome(
            status="verified",
            authority=self.authority_name,
            adapter_name=self.adapter_name,
            reference_no=ref,
            is_simulated=True,
            message=f"Land ownership and continuous parcel status verified in State Land Records for Survey Plot {survey} ({acres} Acres).",
            raw_response={"simulated_code": 200, "status": "RECORD_AUTHENTIC", "survey_plot": survey, "registered_area_acres": acres}
        )
