"""Pydantic schemas for Dashboard API."""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field


class DashboardCentresSummary(BaseModel):
    """Aggregate centre counts."""
    total: int = 0
    active: int = 0
    inactive: int = 0


class DashboardSessionsSummary(BaseModel):
    """Aggregate monitoring session counts by execution status."""
    total: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


class DashboardAlertsSummary(BaseModel):
    """Aggregate alert counts by review state and category."""
    total: int = 0
    pending: int = 0
    verified: int = 0
    false_positive: int = 0
    attendance_discrepancies: int = 0
    infrastructure_discrepancies: int = 0
    high_severity: int = 0


class DashboardComplianceSummary(BaseModel):
    """Aggregate compliance comparison outcomes."""
    attendance_matches: int = 0
    attendance_discrepancies: int = 0
    attendance_insufficient_data: int = 0
    infrastructure_compliant: int = 0
    infrastructure_discrepancies: int = 0
    infrastructure_insufficient_data: int = 0
    infrastructure_not_monitored: int = 0


class DashboardSummaryResponse(BaseModel):
    """Unified system-wide or centre-scoped dashboard metrics summary."""
    centres: DashboardCentresSummary
    monitoring_sessions: DashboardSessionsSummary
    alerts: DashboardAlertsSummary
    compliance: DashboardComplianceSummary


class CentreOverviewItem(BaseModel):
    """High-level monitoring and compliance status per training centre."""
    id: int
    name: str
    centre_code: str
    location: Optional[str] = None
    status: str
    camera_count: int = 0
    latest_session_id: Optional[int] = None
    latest_session_date: Optional[date] = None
    latest_session_status: Optional[str] = None
    latest_attendance_compliance: Optional[str] = None
    latest_infrastructure_compliance: Optional[str] = None
    pending_alerts_count: int = 0


class RecentActivityItem(BaseModel):
    """Chronological event representing actual database operations."""
    id: str
    activity_type: str  # SESSION_COMPLETED, SESSION_CREATED, COMPLIANCE_CALCULATED, ALERT_GENERATED, ALERT_VERIFIED, ALERT_FALSE_POSITIVE
    title: str
    description: str
    timestamp: datetime
    centre_id: int
    centre_name: str
    centre_code: str
    session_id: Optional[int] = None
    alert_id: Optional[int] = None
