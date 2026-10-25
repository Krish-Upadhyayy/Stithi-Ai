"""SQLAlchemy Database Models for SIH Training Centre AI Monitoring System."""

from backend.app.models.base import BaseModel
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.attendance import AttendanceObservation
from backend.app.models.inventory import InventoryItem
from backend.app.models.infrastructure import InfrastructureObservation
from backend.app.models.alert import Alert, AlertEvidence
from backend.app.models.compliance import (
    AttendanceComplianceResult,
    InfrastructureComplianceResult,
)

__all__ = [
    "BaseModel",
    "User",
    "Centre",
    "Camera",
    "MonitoringSession",
    "Snapshot",
    "AttendanceObservation",
    "InventoryItem",
    "InfrastructureObservation",
    "Alert",
    "AlertEvidence",
    "AttendanceComplianceResult",
    "InfrastructureComplianceResult",
]
