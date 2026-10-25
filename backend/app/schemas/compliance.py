"""Pydantic schemas for the Compliance Engine.

Defines serialized representations of:
1. Attendance compliance checks (Physical vs AI aggregate)
2. Infrastructure compliance checks (Sanctioned inventory vs AI detected assets)
3. Dashboard compliance metrics summary
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AttendanceComplianceSchema(BaseModel):
    """Schema representing attendance compliance evaluation."""
    id: Optional[int] = None
    monitoring_session_id: int
    physical_attendance: int = Field(..., ge=0, description="Self-reported physical headcount count")
    ai_estimated_attendance: Optional[float] = Field(None, description="Robust AI aggregate headcount")
    difference: Optional[float] = Field(None, description="Absolute difference between physical and AI estimate")
    tolerance: int = Field(default=2, ge=0, description="Configured allowed headcount variance")
    aggregation_method: str = Field(default="MEDIAN", description="Aggregation strategy (MEDIAN or MEAN)")
    valid_observation_count: int = Field(default=0, ge=0, description="Valid AI snapshot observations used")
    total_snapshots_considered: int = Field(default=0, ge=0, description="Total completed session snapshots evaluated")
    status: str = Field(..., description="Compliance status: MATCH, DISCREPANCY, or INSUFFICIENT_DATA")
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InfrastructureComplianceItemSchema(BaseModel):
    """Schema representing single inventory asset infrastructure compliance evaluation."""
    id: Optional[int] = None
    monitoring_session_id: int
    inventory_item_id: Optional[int] = None
    item_name: str
    ai_class: Optional[str] = Field(None, description="Mapped canonical AI class or None if unmapped")
    expected_quantity: int = Field(default=0, ge=0, description="Sanctioned baseline requirement")
    observed_quantity: Optional[float] = Field(None, description="Robust AI aggregate visible count")
    difference: Optional[float] = Field(None, description="Variance between expected and observed quantity")
    aggregation_method: str = Field(default="MEDIAN", description="Aggregation strategy (MEDIAN or MEAN)")
    valid_observation_count: int = Field(default=0, ge=0, description="Valid AI snapshot observations for this class")
    total_snapshots_considered: int = Field(default=0, ge=0, description="Total completed session snapshots evaluated")
    status: str = Field(..., description="Status: COMPLIANT, DISCREPANCY, NOT_MONITORED, or INSUFFICIENT_DATA")
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalculateComplianceRequest(BaseModel):
    """Request payload to trigger compliance calculation with optional parameter overrides."""
    tolerance: Optional[int] = Field(None, ge=0, description="Custom attendance tolerance override")
    aggregation_method: Optional[str] = Field(None, description="Custom aggregation override: 'MEDIAN' or 'MEAN'")


class SessionComplianceResponse(BaseModel):
    """Consolidated compliance response for a monitoring session."""
    session_id: int
    calculated_at: Optional[datetime] = None
    attendance: Optional[AttendanceComplianceSchema] = None
    infrastructure: List[InfrastructureComplianceItemSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ComplianceDashboardSummaryResponse(BaseModel):
    """Real database metrics summary for the compliance overview dashboard."""
    total_sessions_evaluated: int = 0
    attendance_matches: int = 0
    attendance_discrepancies: int = 0
    infrastructure_discrepancies: int = 0
    insufficient_data_sessions: int = 0
    last_calculated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
