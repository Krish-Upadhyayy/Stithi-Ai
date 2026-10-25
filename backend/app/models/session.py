"""Monitoring Session database model."""

from datetime import datetime, date
from sqlalchemy import Column, Integer, Float, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class MonitoringSession(BaseModel):
    __tablename__ = "monitoring_sessions"

    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="CASCADE"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Session date (defaults to current calendar date)
    session_date = Column(Date, default=date.today, nullable=False)
    
    # Strictly an anonymous integer count — zero student identities per SRS §FR-03 & PRD §9
    physical_attendance = Column(Integer, nullable=False, default=0)
    
    # Timestamps set when session is explicitly started and completed
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED

    # Audit creator
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Video Source & Inspection Metadata
    video_file_path = Column(String(500), nullable=True)
    video_filename = Column(String(255), nullable=True)
    video_file_size = Column(Integer, nullable=True)
    video_duration_seconds = Column(Float, nullable=True)
    video_fps = Column(Float, nullable=True)
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    video_total_frames = Column(Integer, nullable=True)
    video_processing_status = Column(String(50), nullable=False, default="NOT_STARTED", index=True)  # NOT_STARTED, PROCESSING, COMPLETED, FAILED
    video_error_message = Column(String(500), nullable=True)

    # Relationships
    centre = relationship("Centre", back_populates="monitoring_sessions")
    camera = relationship("Camera", back_populates="monitoring_sessions")
    creator = relationship("User", foreign_keys=[created_by])
    snapshots = relationship("Snapshot", back_populates="monitoring_session", cascade="all, delete-orphan")
    attendance_observations = relationship("AttendanceObservation", back_populates="monitoring_session", cascade="all, delete-orphan")
    infrastructure_observations = relationship("InfrastructureObservation", back_populates="monitoring_session", cascade="all, delete-orphan")
    attendance_compliance = relationship("AttendanceComplianceResult", back_populates="monitoring_session", uselist=False, cascade="all, delete-orphan")
    infrastructure_compliance = relationship("InfrastructureComplianceResult", back_populates="monitoring_session", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="monitoring_session", foreign_keys="Alert.monitoring_session_id", cascade="all, delete-orphan")


