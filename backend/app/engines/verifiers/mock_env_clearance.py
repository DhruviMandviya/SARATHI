from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome

class EnvironmentClearanceVerifier(BaseVerifier):
    authority_name = "State Pollution Control Board / MoEFCC"
    adapter_name = "mock_environment_clearance_adapter"

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
                message="No Consent to Establish / Environment Clearance reference number detected. Pending visual verification.",
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
                message="Pollution Control Board portal sync in progress. Status marked Pending Verification.",
                raw_response={"simulated_code": 504, "endpoint": "https://spcb.gov.in/v2/consent/query"}
            )

        if ref_upper.endswith("REJ") or ref_upper.endswith("00"):
            return VerificationOutcome(
                status="not_verified",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Consent to Establish reference number not found or revoked in State Pollution Board registry.",
                raw_response={"simulated_code": 404, "record_found": False}
            )

        if ref_upper.endswith("PROG"):
            return VerificationOutcome(
                status="in_progress",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Environmental impact and effluent treatment review currently under committee evaluation.",
                raw_response={"simulated_code": 202, "status": "COMMITTEE_EVALUATION"}
            )

        return VerificationOutcome(
            status="verified",
            authority=self.authority_name,
            adapter_name=self.adapter_name,
            reference_no=ref,
            is_simulated=True,
            message="Consent to Establish (CTE) is verified and valid for educational institutional operations.",
            raw_response={"simulated_code": 200, "clearance_status": "VALID", "category": "ORANGE_EDUCATIONAL"}
        )
