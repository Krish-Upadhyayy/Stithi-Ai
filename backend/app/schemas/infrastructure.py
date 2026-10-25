"""Pydantic schemas for YOLO26 Infrastructure AI detection."""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class DetectedAssetSummary(BaseModel):
    """Summary of visibly detected asset counts and confidences for a single class."""
    asset_type: str = Field(..., description="Detected asset class name (e.g. chair, computer, projector)")
    detected_class: str = Field(..., description="Alias matching asset_type")
    count: int = Field(..., description="Visibly detected count in snapshot")
    detected_count: int = Field(..., description="Alias matching count")
    confidence: Optional[float] = Field(None, description="Average confidence score")
    min_confidence: Optional[float] = Field(None)
    max_confidence: Optional[float] = Field(None)
    status: str = Field(default="Visually detected", description="Apparent visual detection state")
    mapped_inventory_item: Optional[str] = Field(None, description="Mapped centre inventory item name if available")


class ProcessSnapshotInfrastructureRequest(BaseModel):
    """Request payload for single-snapshot infrastructure detection."""
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Override model confidence threshold (defaults to 0.40)",
    )
    render_annotated: Optional[bool] = Field(
        default=True,
        description="Render and store visual evidence image with bounding boxes",
    )


class ProcessSessionInfrastructureRequest(BaseModel):
    """Request payload for session-wide infrastructure detection batch processing."""
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Override model confidence threshold (defaults to 0.40)",
    )


class InfrastructureObservationResponse(BaseModel):
    """Schema representing an individual stored InfrastructureObservation record."""
    id: int
    snapshot_id: int
    monitoring_session_id: Optional[int] = None
    inventory_item_id: Optional[int] = None
    asset_type: str
    detected_quantity: int
    detected_class: str
    detected_count: int
    confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    confidence_threshold: Optional[float] = None
    model_name: str
    model_version: str
    inference_time_ms: Optional[float] = None
    inference_device: Optional[str] = None
    processing_status: str
    has_annotated_image: bool = False
    apparent_condition: str = "Visually detected"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SnapshotInfrastructureResponse(BaseModel):
    """Consolidated response for a single snapshot's infrastructure detection run."""
    snapshot_id: int
    monitoring_session_id: int
    detections: List[DetectedAssetSummary]
    observations: List[InfrastructureObservationResponse]
    total_detected_assets: int
    model_name: str
    model_version: str
    inference_time_ms: Optional[float] = None
    status: str  # SUCCESS, WEIGHTS_MISSING, FAILED
    message: Optional[str] = None
    has_annotated_image: bool = False


class ProcessSessionInfrastructureResponse(BaseModel):
    """Response returned upon batch processing all snapshots in a monitoring session."""
    session_id: int
    snapshots_processed: int
    observations_created: int
    detected_summary: Dict[str, int]
    model_name: str
    model_version: str
    status: str
    message: str
