"""Dashboard API routes providing aggregate analytics, centre overviews, and live audit feeds."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    DashboardSummaryResponse,
    CentreOverviewItem,
    RecentActivityItem,
)
from backend.app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get unified monitoring and compliance dashboard metrics",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns real aggregate counts across centres, sessions, alerts, and compliance outcomes.
    
    Data is scoped strictly to authorized centres for CENTRE_USER accounts.
    """
    return DashboardService.get_summary(db=db, user=current_user)


@router.get(
    "/centres-overview",
    response_model=List[CentreOverviewItem],
    summary="Get high-level monitoring and compliance status per centre",
)
def get_centres_overview(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional maximum centres to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Provides per-centre operational snapshot including latest session, status, and pending alert counts."""
    return DashboardService.get_centres_overview(db=db, user=current_user, limit=limit)


@router.get(
    "/recent-activity",
    response_model=List[RecentActivityItem],
    summary="Get chronological timeline of sessions and alert reviews",
)
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of activity events"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns real timestamped audit actions (sessions completed, alerts generated, reviews confirmed)."""
    return DashboardService.get_recent_activity(db=db, user=current_user, limit=limit)
