"""Training Centre database model."""

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Centre(BaseModel):
    __tablename__ = "centres"

    centre_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE, SUSPENDED

    # Relationships
    users = relationship("User", back_populates="centre", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="centre", cascade="all, delete-orphan")
    monitoring_sessions = relationship("MonitoringSession", back_populates="centre", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="centre", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="centre", cascade="all, delete-orphan")

    @property
    def camera_count(self) -> int:
        return len(self.cameras) if self.cameras else 0
