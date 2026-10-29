from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class VerificationOutcome:
    def __init__(
        self,
        status: str,  # verified, in_progress, not_verified, pending
        authority: str,
        adapter_name: str,
        reference_no: Optional[str],
        is_simulated: bool = True,  # ALWAYS True in this MVP
        message: str = "",
        raw_response: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.authority = authority
        self.adapter_name = adapter_name
        self.reference_no = reference_no
        self.is_simulated = is_simulated
        self.message = message
        self.raw_response = raw_response or {}
        self.checked_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "authority": self.authority,
            "adapter_name": self.adapter_name,
            "reference_no": self.reference_no,
            "is_simulated": self.is_simulated,
            "message": self.message,
            "raw_response": self.raw_response,
            "checked_at": self.checked_at.isoformat()
        }

class BaseVerifier(ABC):
    authority_name: str = "Government Authority"
    adapter_name: str = "base_verifier"

    @abstractmethod
    def verify(
        self,
        reference_no: Optional[str],
        document_context: Optional[Dict[str, Any]] = None
    ) -> VerificationOutcome:
        pass
