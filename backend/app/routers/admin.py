from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import require_admin
from backend.app.models.user import User
from backend.app.models.compliance import ComplianceRule
from backend.app.schemas.compliance import ComplianceRuleOut, ComplianceRuleUpdate
from backend.app.services.audit import record_audit_event

router = APIRouter(prefix="/admin", tags=["Admin & Rule Management"])

@router.get("/rules", response_model=List[ComplianceRuleOut])
def list_compliance_rules(
    active_only: bool = Query(True, description="Filter only currently active rules"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(ComplianceRule)
    if active_only:
        query = query.filter(ComplianceRule.active == True)
    return query.order_by(ComplianceRule.rule_key.asc(), ComplianceRule.version.desc()).all()

@router.put("/rules/{rule_id}", response_model=ComplianceRuleOut)
def update_compliance_rule(
    rule_id: int,
    payload: ComplianceRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Non-mutating version update for a compliance rule.
    Deactivates the current version and creates a new incremented version.
    """
    current_rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
    if not current_rule:
        raise HTTPException(status_code=404, detail="Compliance rule not found")

    # Deactivate current version
    current_rule.active = False

    # Create new incremented version
    new_rule = ComplianceRule(
        rule_key=current_rule.rule_key,
        name=current_rule.name,
        clause=current_rule.clause,
        source=current_rule.source,
        program=current_rule.program,
        parameters=payload.parameters if payload.parameters is not None else current_rule.parameters,
        check_type=current_rule.check_type,
        version=current_rule.version + 1,
        active=payload.active if payload.active is not None else True,
        verified_against_handbook=payload.verified_against_handbook if payload.verified_against_handbook is not None else current_rule.verified_against_handbook,
        on_missing_data=current_rule.on_missing_data
    )
    db.add(new_rule)
    db.flush()

    # Append-only audit record
    record_audit_event(
        db=db,
        action="UPDATE_COMPLIANCE_RULE_VERSION",
        entity_type="compliance_rule",
        entity_id=new_rule.id,
        actor=current_user,
        before_state={"rule_id": current_rule.id, "version": current_rule.version, "parameters": current_rule.parameters},
        after_state={
            "rule_key": current_rule.rule_key,
            "version": new_rule.version,
            "parameters": new_rule.parameters
        }
    )

    db.commit()
    db.refresh(new_rule)
    return new_rule
