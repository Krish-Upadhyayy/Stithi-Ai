"""User database model."""

from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="CENTRE_USER")  # ADMIN, CENTRE_USER, REVIEWER
    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    centre = relationship("Centre", back_populates="users")
