"""Pydantic schemas for Compliance Alerts and Evidence."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertEvidenceResponse(BaseModel):
    """Supporting snapshot evidence record attached to a compliance alert."""
    id: int
    alert_id: int
    snapshot_id: int
    sequence_number: Optional[int] = None
    frame_time_seconds: Optional[float] = None
    evidence_type: str  # ATTENDANCE_SNAPSHOT, INFRASTRUCTURE_SNAPSHOT
    observation_id: Optional[int] = None
    annotated_image_path: Optional[str] = None
    has_annotated_image: bool = False
    detected_count: Optional[int] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    """Compliance alert record with full audit and evidence metadata."""
    id: int
    centre_id: int
    centre_name: Optional[str] = None
    centre_code: Optional[str] = None
    session_id: Optional[int] = None
    monitoring_session_id: Optional[int] = None
    snapshot_id: Optional[int] = None
    compliance_result_id: Optional[int] = None
    inventory_item_id: Optional[int] = None
    inventory_item_name: Optional[str] = None

    alert_type: str  # ATTENDANCE_DISCREPANCY, INFRASTRUCTURE_DISCREPANCY
    severity: str    # LOW, MEDIUM, HIGH
    title: str = "Potential Discrepancy Detected"
    description: Optional[str] = None

    expected_value: float = 0.0
    observed_value: float = 0.0
    detected_value: Optional[float] = None
    difference: float = 0.0

    status: str      # PENDING, VERIFIED, FALSE_POSITIVE
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewer_comment: Optional[str] = None

    evidence: List[AlertEvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AlertReviewRequest(BaseModel):
    """Payload submitted by a reviewer to verify or dismiss an alert."""
    status: str = Field(..., description="Target status: 'VERIFIED' or 'FALSE_POSITIVE'")
    reviewer_comment: Optional[str] = Field(None, description="Review justification note (Required for FALSE_POSITIVE)")


class AlertStatusUpdate(BaseModel):
    """Legacy schema for backwards compatibility with test_routes.py."""
    status: str = Field(..., description="PENDING, VERIFIED, or FALSE_POSITIVE")
    reviewer_comment: Optional[str] = None


class AlertGenerationResponse(BaseModel):
    """Summary response from generating alerts for a session."""
    session_id: int
    alerts_created: int
    alerts_existing: int
    alerts: List[AlertResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AlertSummaryResponse(BaseModel):
    """Aggregated alert status and category metrics."""
    total_alerts: int = 0
    pending_alerts: int = 0
    verified_alerts: int = 0
    false_positive_alerts: int = 0
    attendance_discrepancies: int = 0
    infrastructure_discrepancies: int = 0
    high_severity_alerts: int = 0

    model_config = ConfigDict(from_attributes=True)
