"""Pydantic schemas for Centre."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class CentreBase(BaseModel):
    centre_code: str = Field(..., min_length=2, max_length=50, description="Unique centre identifier")
    name: str = Field(..., min_length=2, max_length=150, description="Centre name")
    location: Optional[str] = Field(None, max_length=255, description="Location text / address")
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] = Field(default="ACTIVE", description="Operational status")


class CentreCreate(CentreBase):
    pass


class CentreUpdate(BaseModel):
    centre_code: Optional[str] = Field(None, min_length=2, max_length=50, description="Updated centre code")
    name: Optional[str] = Field(None, min_length=2, max_length=150, description="Updated centre name")
    location: Optional[str] = Field(None, max_length=255, description="Updated location")
    status: Optional[Literal["ACTIVE", "INACTIVE", "SUSPENDED"]] = Field(None, description="Updated status")


class CentreStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] = Field(..., description="Target status")


class CentreResponse(CentreBase):
    id: int
    camera_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
