"""Health schema definitions."""

from typing import Dict, Any
from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str
    service: str
    environment: str
    architecture: str
    version: str
    pipelines: Dict[str, str]
