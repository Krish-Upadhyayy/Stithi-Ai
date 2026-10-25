"""Pydantic schemas for Camera."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class CameraBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Camera feed name")
    source_type: Literal["VIDEO_FILE", "CAMERA"] = Field(default="VIDEO_FILE", description="Source type: VIDEO_FILE or CAMERA")
    source_url: str = Field(..., min_length=1, max_length=500, description="Video path or camera stream URL")
    is_active: bool = Field(default=True, description="Active status")


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Updated camera feed name")
    source_type: Optional[Literal["VIDEO_FILE", "CAMERA"]] = Field(None, description="Updated source type")
    source_url: Optional[str] = Field(None, min_length=1, max_length=500, description="Updated stream URL or path")
    is_active: Optional[bool] = Field(None, description="Updated active status")


class CameraStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Active status")


class CameraResponse(CameraBase):
    id: int
    centre_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
