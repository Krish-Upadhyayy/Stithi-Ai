"""Compliance Alert and Supporting Evidence database models.

Represents empirical discrepancy notices generated strictly from verified Compliance Engine outputs.
Human review lifecycle:
  PENDING -> VERIFIED (human confirmed)
  PENDING -> FALSE_POSITIVE (human dismissed with required justification comment)

Strict Terminology & Legal Constraints:
- Termed 'attendance discrepancy' or 'infrastructure discrepancy'.
- Never labels centre as 'fraudulent' or claims machines are 'mechanically broken'.
- Attached evidence points directly to CCTV snapshots and AI observations without duplicating binary files.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Alert(BaseModel):
    __tablename__ = "alerts"

    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_session_id = Column(Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True)

    # Discrepancy origin reference
    compliance_result_id = Column(Integer, nullable=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True, index=True)

    alert_type = Column(String(50), nullable=False, index=True)  # ATTENDANCE_DISCREPANCY, INFRASTRUCTURE_DISCREPANCY
    severity = Column(String(50), nullable=False, default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH
    title = Column(String(200), nullable=False, default="Potential Discrepancy Detected")
    description = Column(Text, nullable=True)

    # Quantitative metrics
    expected_value = Column(Float, nullable=False, default=0.0)
    observed_value = Column(Float, nullable=False, default=0.0)
    detected_value = Column(Float, nullable=True)
    difference = Column(Float, nullable=False, default=0.0)

    # Human Review Lifecycle: PENDING -> VERIFIED / FALSE_POSITIVE
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_comment = Column(Text, nullable=True)

    # Relationships
    centre = relationship("Centre", back_populates="alerts")
    monitoring_session = relationship("MonitoringSession", back_populates="alerts", foreign_keys=[monitoring_session_id])
    snapshot = relationship("Snapshot", back_populates="alerts")
    inventory_item = relationship("InventoryItem")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    evidence = relationship("AlertEvidence", back_populates="alert", cascade="all, delete-orphan")


class AlertEvidence(BaseModel):
    """Stores supporting snapshot evidence linked to a discrepancy alert."""
    __tablename__ = "alert_evidence"

    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False)  # ATTENDANCE_SNAPSHOT, INFRASTRUCTURE_SNAPSHOT
    observation_id = Column(Integer, nullable=True)     # AttendanceObservation.id or InfrastructureObservation.id

    # Relationships
    alert = relationship("Alert", back_populates="evidence")
    snapshot = relationship("Snapshot")
