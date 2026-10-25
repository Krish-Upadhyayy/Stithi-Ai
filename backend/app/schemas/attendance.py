"""Attendance AI observation and inference request/response schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DetectionBoxSchema(BaseModel):
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box coordinates")
    confidence: float = Field(..., description="Detection confidence score")
    class_name: str = Field(..., description="Generic detected class (e.g., person, face)")


class ProcessSnapshotAttendanceRequest(BaseModel):
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.01,
        le=1.0,
        description="Optional override for detection confidence threshold",
    )


class ProcessSessionAttendanceRequest(BaseModel):
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.01,
        le=1.0,
        description="Optional override for detection confidence threshold",
    )


class AttendanceObservationResponse(BaseModel):
    id: int
    snapshot_id: int
    monitoring_session_id: Optional[int] = None
    observed_count: int = Field(..., description="Anonymous headcount detected in frame")
    detected_count: int = Field(..., description="Synonym for observed_count")
    confidence_score: Optional[float] = Field(None, description="Average detection confidence")
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    confidence_threshold: Optional[float] = None
    model_name: str
    model_version: str
    inference_time_ms: Optional[float] = None
    inference_device: Optional[str] = None
    processing_status: str
    has_annotated_image: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessSessionAttendanceResponse(BaseModel):
    session_id: int
    snapshots_processed: int
    observations_created: int
    model_name: str
    model_version: str
    status: str
    message: str
