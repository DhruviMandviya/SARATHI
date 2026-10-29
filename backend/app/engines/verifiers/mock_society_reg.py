from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome

class SocietyRegistrationVerifier(BaseVerifier):
    authority_name = "Registrar of Societies & Charity Commissioner"
    adapter_name = "mock_society_registration_adapter"

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
                message="Registration number not detected on society certificate. Pending official manual input.",
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
                message="Simulated State Charity Commissioner registry gateway timed out. Status marked Pending.",
                raw_response={"simulated_code": 504, "timeout": True}
            )

        if ref_upper.endswith("REJ") or ref_upper.endswith("00"):
            return VerificationOutcome(
                status="not_verified",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Society registration number not found in simulated state registry records.",
                raw_response={"simulated_code": 404, "status": "NOT_FOUND"}
            )

        if ref_upper.endswith("PROG"):
            return VerificationOutcome(
                status="in_progress",
                authority=self.authority_name,
                adapter_name=self.adapter_name,
                reference_no=ref,
                is_simulated=True,
                message="Annual list of governing body members under review at assistant registrar.",
                raw_response={"simulated_code": 202, "status": "ANNUAL_RETURN_UNDER_REVIEW"}
            )

        return VerificationOutcome(
            status="verified",
            authority=self.authority_name,
            adapter_name=self.adapter_name,
            reference_no=ref,
            is_simulated=True,
            message="Trust / Society is active and in good standing with promoting educational mandate.",
            raw_response={"simulated_code": 200, "status": "ACTIVE_REGISTERED", "trust_type": "EDUCATIONAL"}
        )
