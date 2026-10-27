from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

class ComplianceRuleOut(BaseModel):
    id: int
    rule_key: str
    name: str
    clause: str
    source: str
    program: str
    parameters: Dict[str, Any]
    check_type: str
    version: int
    active: bool
    verified_against_handbook: bool
    on_missing_data: str

    model_config = ConfigDict(from_attributes=True)

class ComplianceRuleUpdate(BaseModel):
    parameters: Dict[str, Any]
    active: Optional[bool] = True
    verified_against_handbook: Optional[bool] = False

class ComplianceResultOut(BaseModel):
    id: int
    application_id: int
    rule_id: int
    rule_version: int
    required_value: str
    provided_value: Optional[str] = None
    outcome: str
    explanation: str
    rule: Optional[ComplianceRuleOut] = None

    model_config = ConfigDict(from_attributes=True)
