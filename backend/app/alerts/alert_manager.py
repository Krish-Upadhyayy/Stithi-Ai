"""Alert Manager foundation.

Manages evidence-backed compliance alerts.
Statuses: Pending, Verified, False Positive.
"""

from typing import Dict, Any, Optional
from enum import Enum


class AlertStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    FALSE_POSITIVE = "False Positive"


class AlertType(str, Enum):
    ATTENDANCE_DISCREPANCY = "Attendance Discrepancy"
    INFRASTRUCTURE_DISCREPANCY = "Infrastructure Discrepancy"


class AlertManager:
    """Orchestrates discrepancy alert creation and reviewer status updates."""

    @staticmethod
    def build_attendance_alert(
        centre_id: str,
        session_id: str,
        reported_count: int,
        observed_count: int,
        snapshot_path: str
    ) -> Dict[str, Any]:
        difference = reported_count - observed_count
        return {
            "centre_id": centre_id,
            "session_id": session_id,
            "type": AlertType.ATTENDANCE_DISCREPANCY.value,
            "severity": "HIGH" if abs(difference) > 5 else "MEDIUM",
            "expected_value": reported_count,
            "observed_value": observed_count,
            "difference": difference,
            "snapshot_path": snapshot_path,
            "status": AlertStatus.PENDING.value
        }
