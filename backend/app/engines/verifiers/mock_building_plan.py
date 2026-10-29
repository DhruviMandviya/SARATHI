from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome

class BuildingPlanVerifier(BaseVerifier):
    authority_name = "Competent Municipal / Town Planning Authority"
    adapter_name = "mock_municipal_building_plan_adapter"

    def verify(
        self,
        reference_no: Optional[str],
        document_context: Optional[Dict[str, Any]] = None
    ) -> VerificationOutcome:
        ref = (reference_no or "").strip()

        if not ref:
            return VerificationOutcome(
                status="pending",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=None,
                is_simulated=True,
                message="No municipal plan sanction reference number extracted. Verification pending visual manual entry.",
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
                message="Simulated Municipal Corporation Town Planning server timed out. Marked Pending Verification.",
                raw_response={"simulated_code": 504, "endpoint": "https://api.municipal.gov.in/v1/sanction/verify"}
            )

        if ref_upper.endswith("REJ") or ref_upper.endswith("00"):
            return VerificationOutcome(
                status="not_verified",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Sanction order reference not found in municipal building plan repository.",
                raw_response={"simulated_code": 404, "record_found": False}
            )

        if ref_upper.endswith("PROG"):
            return VerificationOutcome(
                status="in_progress",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Municipal building sanction application is currently under scrutiny at the zonal office.",
                raw_response={"simulated_code": 202, "application_status": "under_zonal_scrutiny"}
            )

        return VerificationOutcome(
            status="verified",
            authority=self.authority_name,
            adapter_name=self.adapter_name,
            reference_no=ref,
            is_simulated=True,
            message="Municipal sanction verified. Built-up area and institutional zoning approved in simulated registry.",
            raw_response={"simulated_code": 200, "sanction_status": "APPROVED", "authority_code": "MUN-TP-2024"}
        )
