"""Pydantic schemas for MonitoringSession."""

from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


SessionStatusType = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


class MonitoringSessionBase(BaseModel):
    centre_id: int = Field(..., description="Target Training Centre ID")
    camera_id: Optional[int] = Field(default=None, description="Target Camera ID belonging to the centre")
    # Strictly an anonymous headcount number per SRS §FR-03 & PRD §9
    physical_attendance: int = Field(..., ge=0, description="Physically verified aggregate headcount (non-negative integer)")
    session_date: Optional[date] = Field(default=None, description="Calendar date of monitoring session")


class MonitoringSessionCreate(MonitoringSessionBase):
    pass


class CentreSummary(BaseModel):
    id: int
    centre_code: str
    name: str
    location: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CameraSummary(BaseModel):
    id: int
    name: str
    source_type: str
    source_url: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CreatorSummary(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class MonitoringSessionResponse(BaseModel):
    id: int
    centre_id: int
    camera_id: Optional[int] = None
    session_date: date
    physical_attendance: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str
    created_by: Optional[int] = None
    
    # Video Source & Inspection Metadata
    video_file_path: Optional[str] = None
    video_filename: Optional[str] = None
    video_file_size: Optional[int] = None
    video_duration_seconds: Optional[float] = None
    video_fps: Optional[float] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_total_frames: Optional[int] = None
    video_processing_status: str = "NOT_STARTED"
    video_error_message: Optional[str] = None
    snapshots_count: Optional[int] = 0

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitoringSessionDetailResponse(MonitoringSessionResponse):
    centre: Optional[CentreSummary] = None
    camera: Optional[CameraSummary] = None
    creator: Optional[CreatorSummary] = None

    model_config = ConfigDict(from_attributes=True)
