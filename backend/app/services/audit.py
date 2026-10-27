from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditLog
from backend.app.models.user import User

def record_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    actor: Optional[User] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Append-only audit event recording.
    There are no code paths for updating or deleting audit logs anywhere in the system.
    """
    actor_id = actor.id if actor else None
    actor_role = actor.role if actor else "system"

    log_entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
