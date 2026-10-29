from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import require_official_or_auditor
from backend.app.models.user import User
from backend.app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = "System"
    actor_role: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[AuditLogOut])
def get_audit_trail(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (application, document, decision, etc.)"),
    entity_id: Optional[int] = Query(None, description="Filter by specific entity ID"),
    actor_role: Optional[str] = Query(None, description="Filter by actor role"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official_or_auditor)
):
    """
    Query the append-only audit trail.
    Accessible strictly to Official, Admin, and Auditor roles.
    There are no endpoints for creating, updating, or deleting audit records.
    """
    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if actor_role:
        query = query.filter(AuditLog.actor_role == actor_role)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    result = []
    for l in logs:
        actor_name = l.actor.full_name if l.actor else ("System Automated Job" if l.actor_role == "system" else "User")
        result.append(AuditLogOut(
            id=l.id,
            actor_id=l.actor_id,
            actor_name=actor_name,
            actor_role=l.actor_role,
            action=l.action,
            entity_type=l.entity_type,
            entity_id=l.entity_id,
            before_state=l.before_state,
            after_state=l.after_state,
            timestamp=l.timestamp
        ))

    return result
