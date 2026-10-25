"""Pydantic schemas for User and Authentication."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    role: str = Field(default="CENTRE_USER", description="ADMIN, CENTRE_USER, REVIEWER")
    centre_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Plaintext password to hash")


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User account email")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
