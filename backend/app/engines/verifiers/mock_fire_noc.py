from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome

class FireNOCVerifier(BaseVerifier):
    authority_name = "State Directorate of Fire & Emergency Services"
    adapter_name = "mock_fire_noc_adapter"

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
                message="No Fire NOC certificate reference number detected in extracted data. Pending manual verification.",
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
                message="State Fire Services dispatch server unreachable. Status marked Pending Verification.",
                raw_response={"simulated_code": 503, "endpoint": "https://fireservices.gov.in/api/v2/noc/status"}
            )

        if ref_upper.endswith("REJ") or ref_upper.endswith("00"):
            return VerificationOutcome(
                status="not_verified",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Fire NOC reference number not found in State Fire Directorate records.",
                raw_response={"simulated_code": 404, "record_found": False}
            )

        if ref_upper.endswith("PROG"):
            return VerificationOutcome(
                status="in_progress",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="On-site fire equipment audit inspection scheduled by divisional fire officer.",
                raw_response={"simulated_code": 202, "status": "INSPECTION_SCHEDULED"}
            )

        return VerificationOutcome(
            status="verified",
            authority=self.authority_name,
            adapter_name=self.adapter_name,
            reference_no=ref,
            is_simulated=True,
            message="Fire Safety clearance certificate is active and authentic in State Fire Records.",
            raw_response={"simulated_code": 200, "noc_status": "VALID", "hazard_class": "EDUCATIONAL_BUILDING"}
        )
