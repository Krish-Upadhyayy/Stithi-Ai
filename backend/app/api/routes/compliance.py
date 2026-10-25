"""Compliance Engine API Endpoints.

Compares:
1. Physical headcount vs robust AI attendance observation estimate
2. Sanctioned baseline inventory vs robust AI infrastructure observations

Strict Constraints:
- Terminology: 'attendance discrepancy' or 'attendance mismatch'.
- Visual presence only: zero claim of mechanical or electrical equipment operability.
- Alerts workflow is decoupled (Prompt 13).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.session import MonitoringSession
from backend.app.models.user import User
from backend.app.schemas.compliance import (
    CalculateComplianceRequest,
    SessionComplianceResponse,
    AttendanceComplianceSchema,
    InfrastructureComplianceItemSchema,
    ComplianceDashboardSummaryResponse,
)
from backend.app.services.compliance_service import ComplianceService

router = APIRouter(tags=["Compliance Engine"])


def verify_session_access(session_id: int, db: Session, user: User) -> MonitoringSession:
    """Verifies that the session exists and current user has authorization to view/manage it."""
    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session #{session_id} not found.",
        )
    if user.role != "ADMIN" and user.centre_id != session.centre_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access data for this centre.",
        )
    return session


@router.post(
    "/monitoring/sessions/{session_id}/compliance/calculate",
    response_model=SessionComplianceResponse,
    summary="Calculate attendance and infrastructure compliance for a session",
)
def calculate_session_compliance(
    session_id: int,
    request_data: Optional[CalculateComplianceRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculates attendance and infrastructure compliance using robust snapshot aggregation.
    
    Idempotent: Replaces previous compliance results for this session without creating duplicates.
    """
    verify_session_access(session_id, db, current_user)

    tolerance = request_data.tolerance if request_data else None
    method = request_data.aggregation_method if request_data else None

    att_result, infra_results = ComplianceService.calculate_and_save_session_compliance(
        db=db,
        session_id=session_id,
        tolerance=tolerance,
        method=method,
    )

    return SessionComplianceResponse(
        session_id=session_id,
        calculated_at=att_result.calculated_at,
        attendance=AttendanceComplianceSchema.model_validate(att_result),
        infrastructure=[
            InfrastructureComplianceItemSchema.model_validate(item) for item in infra_results
        ],
    )


@router.get(
    "/monitoring/sessions/{session_id}/compliance",
    response_model=SessionComplianceResponse,
    summary="Get existing compliance evaluation results for a session",
)
def get_session_compliance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves stored attendance and infrastructure compliance records for a session."""
    verify_session_access(session_id, db, current_user)

    att_result, infra_results = ComplianceService.get_session_compliance(db, session_id)

    calculated_time = att_result.calculated_at if att_result else None

    return SessionComplianceResponse(
        session_id=session_id,
        calculated_at=calculated_time,
        attendance=(
            AttendanceComplianceSchema.model_validate(att_result) if att_result else None
        ),
        infrastructure=[
            InfrastructureComplianceItemSchema.model_validate(item) for item in infra_results
        ],
    )


@router.get(
    "/monitoring/compliance/summary",
    response_model=ComplianceDashboardSummaryResponse,
    summary="Get aggregated compliance statistics across all evaluated sessions",
)
def get_compliance_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exposes real database metrics summary for compliance evaluations."""
    stats = ComplianceService.get_dashboard_summary(db)
    return ComplianceDashboardSummaryResponse(**stats)
