"""Compliance Result database models.

Represents empirical compliance calculation outputs comparing:
1. Physical headcount vs AI-observed attendance (AttendanceComplianceResult)
2. Sanctioned inventory expectations vs AI-detected infrastructure presence (InfrastructureComplianceResult)

Strict Terminology & Legal Constraints:
- Discrepancies are termed 'attendance discrepancy' or 'attendance mismatch'.
- Visual detection establishes apparent presence only; zero claim of mechanical/electrical operation.
- Alerts are decoupled and handled in subsequent workflows (Prompt 13).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class AttendanceComplianceResult(BaseModel):
    """Stores the aggregated attendance compliance comparison for a monitoring session."""
    __tablename__ = "attendance_compliance_results"

    monitoring_session_id = Column(
        Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Comparison metrics
    physical_attendance = Column(Integer, nullable=False)
    ai_estimated_attendance = Column(Float, nullable=True)  # Median or Mean aggregate
    difference = Column(Float, nullable=True)               # abs(physical - ai_estimated)
    tolerance = Column(Integer, nullable=False, default=2)

    # Audit & Cross-snapshot consistency metadata
    aggregation_method = Column(String(50), nullable=False, default="MEDIAN")  # MEDIAN, MEAN
    valid_observation_count = Column(Integer, nullable=False, default=0)
    total_snapshots_considered = Column(Integer, nullable=False, default=0)
    
    # Status: MATCH, DISCREPANCY, INSUFFICIENT_DATA
    status = Column(String(50), nullable=False, default="INSUFFICIENT_DATA", index=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    monitoring_session = relationship("MonitoringSession", back_populates="attendance_compliance")


class InfrastructureComplianceResult(BaseModel):
    """Stores the item-by-item infrastructure compliance comparison for a monitoring session."""
    __tablename__ = "infrastructure_compliance_results"

    monitoring_session_id = Column(
        Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inventory_item_id = Column(
        Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Item & AI Class mapping
    item_name = Column(String(150), nullable=False)
    ai_class = Column(String(100), nullable=True)  # None if NOT_MONITORED

    # Comparison metrics
    expected_quantity = Column(Integer, nullable=False, default=0)
    observed_quantity = Column(Float, nullable=True)  # Median or Mean aggregate
    difference = Column(Float, nullable=True)         # expected - observed

    # Audit & Cross-snapshot consistency metadata
    aggregation_method = Column(String(50), nullable=False, default="MEDIAN")  # MEDIAN, MEAN
    valid_observation_count = Column(Integer, nullable=False, default=0)
    total_snapshots_considered = Column(Integer, nullable=False, default=0)

    # Status: COMPLIANT, DISCREPANCY, NOT_MONITORED, INSUFFICIENT_DATA
    status = Column(String(50), nullable=False, default="INSUFFICIENT_DATA", index=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    monitoring_session = relationship("MonitoringSession", back_populates="infrastructure_compliance")
    inventory_item = relationship("InventoryItem")
