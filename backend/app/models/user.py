from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # institution, official, admin, auditor
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    institution = relationship("Institution", back_populates="users")
