from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    trust_name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    state = Column(String(100), nullable=False)
    aicte_id = Column(String(50), unique=True, index=True, nullable=False)

    users = relationship("User", back_populates="institution")
    applications = relationship("Application", back_populates="institution")
