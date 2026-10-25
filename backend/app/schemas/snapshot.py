"""Pydantic schemas for Snapshot and Video Processing Engine."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SnapshotResponse(BaseModel):
    id: int
    monitoring_session_id: int
    file_path: str
    captured_at: datetime
    sequence_number: int
    frame_time_seconds: Optional[float] = 0.0
    width: Optional[int] = None
    height: Optional[int] = None
    processing_status: str
    created_at: datetime
    view_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VideoUploadResponse(BaseModel):
    session_id: int
    video_filename: str
    file_size: int
    duration_seconds: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    total_frames: Optional[int] = None
    video_processing_status: str = "NOT_STARTED"
    message: str


class VideoProcessRequest(BaseModel):
    interval_seconds: Optional[int] = Field(default=None, ge=1, le=3600, description="Periodic snapshot interval in seconds")
    max_snapshots: Optional[int] = Field(default=None, ge=1, le=1000, description="Maximum snapshots to extract")


class VideoProcessResponse(BaseModel):
    session_id: int
    snapshots_created: int
    duration_seconds: float
    interval_seconds: int
    video_processing_status: str
    message: str
    snapshots: List[SnapshotResponse] = []
