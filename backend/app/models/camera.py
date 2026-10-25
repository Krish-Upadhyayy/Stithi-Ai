"""Camera / Video source database model."""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Camera(BaseModel):
    __tablename__ = "cameras"

    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False, default="VIDEO_FILE")  # VIDEO_FILE, CAMERA
    source_url = Column(String(500), nullable=False)  # local file path or stream URL
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    centre = relationship("Centre", back_populates="cameras")
    monitoring_sessions = relationship("MonitoringSession", back_populates="camera")
