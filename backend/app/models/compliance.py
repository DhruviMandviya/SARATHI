from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_key = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    clause = Column(String(100), nullable=False)
    source = Column(String(255), nullable=False) # e.g. AICTE Approval Process Handbook (APH)
    program = Column(String(100), default="Engineering & Technology", nullable=False)
    parameters = Column(JSON, default=dict, nullable=False)
    check_type = Column(String(50), nullable=False) # min_value, ratio_max, boolean_present, enum_match, etc.
    version = Column(Integer, default=1, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    verified_against_handbook = Column(Boolean, default=False, nullable=False)
    on_missing_data = Column(String(50), default="needs_review", nullable=False)

    results = relationship("ComplianceResult", back_populates="rule")

class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("compliance_rules.id"), nullable=False)
    rule_version = Column(Integer, nullable=False)
    required_value = Column(String(255), nullable=False)
    provided_value = Column(String(255), nullable=True)
    outcome = Column(String(50), nullable=False) # compliant, needs_review, needs_update, non_compliant
    explanation = Column(String(1000), nullable=False)

    application = relationship("Application", back_populates="compliance_results")
    rule = relationship("ComplianceRule", back_populates="results")
