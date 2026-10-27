from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null for system background jobs
    actor_role = Column(String(50), nullable=False) # system, institution, official, admin, auditor
    action = Column(String(100), nullable=False) # e.g. login, document_upload, field_correction, flag_dismiss, decision_recorded, rule_updated
    entity_type = Column(String(100), nullable=False) # application, document, extracted_field, flag, decision, compliance_rule
    entity_id = Column(Integer, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    actor = relationship("User")
