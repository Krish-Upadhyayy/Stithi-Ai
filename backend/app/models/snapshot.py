"""Snapshot database model."""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Snapshot(BaseModel):
    __tablename__ = "snapshots"

    monitoring_session_id = Column(Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sequence_number = Column(Integer, nullable=False, default=1)
    frame_time_seconds = Column(Float, nullable=True, default=0.0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    processing_status = Column(String(50), nullable=False, default="PENDING", index=True)  # PENDING, PROCESSING, COMPLETED, FAILED

    # Relationships
    monitoring_session = relationship("MonitoringSession", back_populates="snapshots")
    attendance_observations = relationship("AttendanceObservation", back_populates="snapshot", cascade="all, delete-orphan")
    infrastructure_observations = relationship("InfrastructureObservation", back_populates="snapshot", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="snapshot")

