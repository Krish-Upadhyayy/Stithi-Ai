"""Attendance Observation database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class AttendanceObservation(BaseModel):
    __tablename__ = "attendance_observations"

    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_session_id = Column(Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Strictly anonymous counting. Zero student identities stored.
    observed_count = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Float, nullable=True)  # Average detection confidence
    min_confidence = Column(Float, nullable=True)
    max_confidence = Column(Float, nullable=True)
    confidence_threshold = Column(Float, nullable=True, default=0.40)
    
    # Model tracking metadata
    model_name = Column(String(100), nullable=False, default="YOLO26-Face-Presence")
    model_version = Column(String(100), nullable=False, default="v1-baseline")
    inference_time_ms = Column(Float, nullable=True)
    inference_device = Column(String(50), nullable=True, default="cpu")
    
    # Processing lifecycle & evidence output
    processing_status = Column(String(50), nullable=False, default="COMPLETED", index=True)  # COMPLETED, FAILED
    annotated_image_path = Column(String(500), nullable=True)
    detection_metadata = Column(Text, nullable=True)  # JSON-encoded bounding boxes and class labels (zero identities)

    # Relationships
    snapshot = relationship("Snapshot", back_populates="attendance_observations")
    monitoring_session = relationship("MonitoringSession", back_populates="attendance_observations")

    @property
    def detected_count(self) -> int:
        """Alias for observed_count matching Prompt 9 terminology."""
        return self.observed_count
