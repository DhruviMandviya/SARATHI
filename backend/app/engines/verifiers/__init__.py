from typing import Dict, Any, Optional
from backend.app.engines.verifiers.base import BaseVerifier, VerificationOutcome
from backend.app.engines.verifiers.mock_building_plan import BuildingPlanVerifier
from backend.app.engines.verifiers.mock_fire_noc import FireNOCVerifier
from backend.app.engines.verifiers.mock_society_reg import SocietyRegistrationVerifier
from backend.app.engines.verifiers.mock_env_clearance import EnvironmentClearanceVerifier
from backend.app.engines.verifiers.mock_land_records import LandRecordsVerifier

REGISTRY = {
    "land_document": LandRecordsVerifier(),
    "building_plan": BuildingPlanVerifier(),
    "fire_noc": FireNOCVerifier(),
    "society_registration": SocietyRegistrationVerifier(),
    "trust_deed": SocietyRegistrationVerifier(),
    "environmental_clearance": EnvironmentClearanceVerifier(),
    "env_clearance": EnvironmentClearanceVerifier(),
    "occupancy_certificate": BuildingPlanVerifier(),
}

def get_verifier_for_doc_type(doc_type: str) -> Optional[BaseVerifier]:
    return REGISTRY.get(doc_type)

def verify_document(doc_type: str, reference_no: Optional[str], document_context: Optional[Dict[str, Any]] = None) -> VerificationOutcome:
    verifier = get_verifier_for_doc_type(doc_type)
    if not verifier:
        if doc_type == "affidavit":
            msg = "Sworn statutory compliance affidavit is self-attested; requires official scrutiny committee review rather than external database lookup."
        else:
            msg = f"No automated verification adapter configured for document type '{doc_type}'. Pending manual review."
        return VerificationOutcome(
            status="pending",
            authority="External Authority Repository",
            adapter_name="generic_pending_adapter",
            reference_no=reference_no,
            is_simulated=True,
            message=msg,
            raw_response={"supported": False, "doc_type": doc_type}
        )
    return verifier.verify(reference_no=reference_no, document_context=document_context)
