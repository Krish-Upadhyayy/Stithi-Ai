"""Infrastructure Observation database model.

Represents empirical detection records of visibly present sanctioned infrastructure
assets extracted from training centre snapshots using YOLO26.
Strict Constraint: Records apparent visual presence and count only. Zero claim of mechanical/electrical functionality.
"""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class InfrastructureObservation(BaseModel):
    __tablename__ = "infrastructure_observations"

    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_session_id = Column(Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Detected asset classification and count
    asset_type = Column(String(100), nullable=False, index=True)  # e.g. chair, computer, projector
    detected_quantity = Column(Integer, nullable=False, default=0)
    
    # Confidence metrics
    confidence = Column(Float, nullable=True)  # Average confidence score
    min_confidence = Column(Float, nullable=True)
    max_confidence = Column(Float, nullable=True)
    confidence_threshold = Column(Float, nullable=True, default=0.40)
    
    # Model tracking metadata
    model_name = Column(String(100), nullable=False, default="YOLO26-Infrastructure")
    model_version = Column(String(100), nullable=False, default="v1-baseline")
    inference_time_ms = Column(Float, nullable=True)
    inference_device = Column(String(50), nullable=True, default="cpu")
    
    # Evidence & lifecycle state
    processing_status = Column(String(50), nullable=False, default="COMPLETED", index=True)  # COMPLETED, FAILED
    annotated_image_path = Column(String(500), nullable=True)
    bounding_boxes = Column(Text, nullable=True)  # JSON-encoded detected boxes with coordinates & scores

    # Relationships
    snapshot = relationship("Snapshot", back_populates="infrastructure_observations")
    monitoring_session = relationship("MonitoringSession", back_populates="infrastructure_observations")
    inventory_item = relationship("InventoryItem", back_populates="infrastructure_observations")

    @property
    def detected_class(self) -> str:
        """Alias for asset_type matching Prompt 11 specification."""
        return self.asset_type

    @property
    def detected_count(self) -> int:
        """Alias for detected_quantity matching Prompt 11 specification."""
        return self.detected_quantity
