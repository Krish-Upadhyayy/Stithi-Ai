"""Dashboard service providing aggregated metrics, centre overviews, and live audit activity.

All counts and metrics are derived strictly from persisted database rows.
Zero synthetic or hardcoded metrics are returned.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.alert import Alert
from backend.app.models.compliance import (
    AttendanceComplianceResult,
    InfrastructureComplianceResult,
)
from backend.app.schemas.dashboard import (
    DashboardCentresSummary,
    DashboardSessionsSummary,
    DashboardAlertsSummary,
    DashboardComplianceSummary,
    DashboardSummaryResponse,
    CentreOverviewItem,
    RecentActivityItem,
)


class DashboardService:
    """Service handling multi-domain dashboard summaries with role-based isolation."""

    @staticmethod
    def get_summary(db: Session, user: User) -> DashboardSummaryResponse:
        """Retrieves verified database aggregates with role-based data isolation."""
        # 1. Centres metrics
        c_query = db.query(Centre)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            c_query = c_query.filter(Centre.id == user.centre_id)

        total_centres = c_query.count()
        active_centres = c_query.filter(Centre.status == "ACTIVE").count()
        inactive_centres = c_query.filter(Centre.status != "ACTIVE").count()

        # 2. Monitoring sessions metrics
        s_query = db.query(MonitoringSession)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            s_query = s_query.filter(MonitoringSession.centre_id == user.centre_id)

        total_sessions = s_query.count()
        pending_sessions = s_query.filter(MonitoringSession.status == "PENDING").count()
        running_sessions = s_query.filter(MonitoringSession.status == "RUNNING").count()
        completed_sessions = s_query.filter(MonitoringSession.status == "COMPLETED").count()
        failed_sessions = s_query.filter(MonitoringSession.status == "FAILED").count()

        # 3. Alerts metrics
        a_query = db.query(Alert)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            a_query = a_query.filter(Alert.centre_id == user.centre_id)

        total_alerts = a_query.count()
        pending_alerts = a_query.filter(Alert.status == "PENDING").count()
        verified_alerts = a_query.filter(Alert.status == "VERIFIED").count()
        false_positive_alerts = a_query.filter(Alert.status == "FALSE_POSITIVE").count()
        att_discrepancy_alerts = a_query.filter(Alert.alert_type == "ATTENDANCE_DISCREPANCY").count()
        infra_discrepancy_alerts = a_query.filter(Alert.alert_type == "INFRASTRUCTURE_DISCREPANCY").count()
        high_sev_alerts = a_query.filter(Alert.severity == "HIGH").count()

        # 4. Compliance metrics
        # Attendance compliance
        att_comp_query = db.query(AttendanceComplianceResult)
        infra_comp_query = db.query(InfrastructureComplianceResult)

        if user.role == "CENTRE_USER" and user.centre_id is not None:
            att_comp_query = att_comp_query.join(
                MonitoringSession, AttendanceComplianceResult.monitoring_session_id == MonitoringSession.id
            ).filter(MonitoringSession.centre_id == user.centre_id)

            infra_comp_query = infra_comp_query.join(
                MonitoringSession, InfrastructureComplianceResult.monitoring_session_id == MonitoringSession.id
            ).filter(MonitoringSession.centre_id == user.centre_id)

        att_matches = att_comp_query.filter(AttendanceComplianceResult.status == "MATCH").count()
        att_discrepancies = att_comp_query.filter(AttendanceComplianceResult.status == "DISCREPANCY").count()
        att_insufficient = att_comp_query.filter(AttendanceComplianceResult.status == "INSUFFICIENT_DATA").count()

        infra_compliant = infra_comp_query.filter(InfrastructureComplianceResult.status == "COMPLIANT").count()
        infra_discrepancies = infra_comp_query.filter(InfrastructureComplianceResult.status == "DISCREPANCY").count()
        infra_insufficient = infra_comp_query.filter(InfrastructureComplianceResult.status == "INSUFFICIENT_DATA").count()
        infra_not_monitored = infra_comp_query.filter(InfrastructureComplianceResult.status == "NOT_MONITORED").count()

        return DashboardSummaryResponse(
            centres=DashboardCentresSummary(
                total=total_centres,
                active=active_centres,
                inactive=inactive_centres,
            ),
            monitoring_sessions=DashboardSessionsSummary(
                total=total_sessions,
                pending=pending_sessions,
                running=running_sessions,
                completed=completed_sessions,
                failed=failed_sessions,
            ),
            alerts=DashboardAlertsSummary(
                total=total_alerts,
                pending=pending_alerts,
                verified=verified_alerts,
                false_positive=false_positive_alerts,
                attendance_discrepancies=att_discrepancy_alerts,
                infrastructure_discrepancies=infra_discrepancy_alerts,
                high_severity=high_sev_alerts,
            ),
            compliance=DashboardComplianceSummary(
                attendance_matches=att_matches,
                attendance_discrepancies=att_discrepancies,
                attendance_insufficient_data=att_insufficient,
                infrastructure_compliant=infra_compliant,
                infrastructure_discrepancies=infra_discrepancies,
                infrastructure_insufficient_data=infra_insufficient,
                infrastructure_not_monitored=infra_not_monitored,
            ),
        )

    @staticmethod
    def get_centres_overview(db: Session, user: User, limit: Optional[int] = None) -> List[CentreOverviewItem]:
        """Provides per-centre operational snapshot including latest session & compliance status."""
        query = db.query(Centre)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            query = query.filter(Centre.id == user.centre_id)

        centres = query.order_by(Centre.name.asc())
        if limit:
            centres = centres.limit(limit)
        centres = centres.all()

        results: List[CentreOverviewItem] = []
        for c in centres:
            cam_count = db.query(Camera).filter(Camera.centre_id == c.id).count()
            latest_session = (
                db.query(MonitoringSession)
                .filter(MonitoringSession.centre_id == c.id)
                .order_by(desc(MonitoringSession.id))
                .first()
            )

            latest_att_comp = None
            latest_infra_comp = None
            if latest_session:
                att_res = (
                    db.query(AttendanceComplianceResult)
                    .filter(AttendanceComplianceResult.monitoring_session_id == latest_session.id)
                    .first()
                )
                if att_res:
                    latest_att_comp = att_res.status

                infra_results = (
                    db.query(InfrastructureComplianceResult)
                    .filter(InfrastructureComplianceResult.monitoring_session_id == latest_session.id)
                    .all()
                )
                if infra_results:
                    statuses = {i.status for i in infra_results}
                    if "DISCREPANCY" in statuses:
                        latest_infra_comp = "DISCREPANCY"
                    elif "COMPLIANT" in statuses:
                        latest_infra_comp = "COMPLIANT"
                    elif "INSUFFICIENT_DATA" in statuses:
                        latest_infra_comp = "INSUFFICIENT_DATA"
                    elif "NOT_MONITORED" in statuses:
                        latest_infra_comp = "NOT_MONITORED"

            pending_alerts = (
                db.query(Alert)
                .filter(Alert.centre_id == c.id, Alert.status == "PENDING")
                .count()
            )

            results.append(
                CentreOverviewItem(
                    id=c.id,
                    name=c.name,
                    centre_code=c.centre_code,
                    location=c.location,
                    status=c.status,
                    camera_count=cam_count,
                    latest_session_id=latest_session.id if latest_session else None,
                    latest_session_date=latest_session.session_date if latest_session else None,
                    latest_session_status=latest_session.status if latest_session else None,
                    latest_attendance_compliance=latest_att_comp,
                    latest_infrastructure_compliance=latest_infra_comp,
                    pending_alerts_count=pending_alerts,
                )
            )

        return results

    @staticmethod
    def get_recent_activity(db: Session, user: User, limit: int = 10) -> List[RecentActivityItem]:
        """Collects real timeline events across monitoring and alert verification."""
        events: List[RecentActivityItem] = []

        # 1. Fetch recent monitoring sessions
        s_query = db.query(MonitoringSession).join(Centre, MonitoringSession.centre_id == Centre.id)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            s_query = s_query.filter(MonitoringSession.centre_id == user.centre_id)

        recent_sessions = s_query.order_by(desc(MonitoringSession.id)).limit(limit).all()

        for s in recent_sessions:
            event_type = "SESSION_COMPLETED" if s.status == "COMPLETED" else "SESSION_CREATED"
            title = f"Monitoring Session #{s.id} ({s.status})"
            desc_text = (
                f"Session at {s.centre.name} with recorded physical headcount {s.physical_attendance}."
                if s.centre else f"Session #{s.id} recorded."
            )
            ts = s.ended_at or s.started_at or s.created_at
            events.append(
                RecentActivityItem(
                    id=f"session-{s.id}-{s.status}",
                    activity_type=event_type,
                    title=title,
                    description=desc_text,
                    timestamp=ts,
                    centre_id=s.centre_id,
                    centre_name=s.centre.name if s.centre else "Unknown",
                    centre_code=s.centre.centre_code if s.centre else "N/A",
                    session_id=s.id,
                    alert_id=None,
                )
            )

        # 2. Fetch recent alerts
        a_query = db.query(Alert).join(Centre, Alert.centre_id == Centre.id)
        if user.role == "CENTRE_USER" and user.centre_id is not None:
            a_query = a_query.filter(Alert.centre_id == user.centre_id)

        recent_alerts = a_query.order_by(desc(Alert.id)).limit(limit).all()

        for a in recent_alerts:
            if a.status == "VERIFIED":
                event_type = "ALERT_VERIFIED"
                title = f"Alert #{a.id} Confirmed (VERIFIED)"
                desc_text = (
                    f"Human reviewer verified {a.alert_type.replace('_', ' ').lower()} at {a.centre.name}."
                    if a.centre else f"Alert #{a.id} verified."
                )
                ts = a.reviewed_at or a.updated_at or a.created_at
            elif a.status == "FALSE_POSITIVE":
                event_type = "ALERT_FALSE_POSITIVE"
                title = f"Alert #{a.id} Dismissed (FALSE_POSITIVE)"
                desc_text = (
                    f"Reviewer dismissed discrepancy with comment: \"{a.reviewer_comment or 'Dismissed'}\""
                )
                ts = a.reviewed_at or a.updated_at or a.created_at
            else:
                event_type = "ALERT_GENERATED"
                title = f"Alert #{a.id}: {a.title}"
                desc_text = (
                    f"Potential discrepancy detected with {a.severity} severity at {a.centre.name}."
                    if a.centre else a.description or "Pending alert."
                )
                ts = a.created_at

            events.append(
                RecentActivityItem(
                    id=f"alert-{a.id}-{a.status}",
                    activity_type=event_type,
                    title=title,
                    description=desc_text,
                    timestamp=ts,
                    centre_id=a.centre_id,
                    centre_name=a.centre.name if a.centre else "Unknown",
                    centre_code=a.centre.centre_code if a.centre else "N/A",
                    session_id=a.monitoring_session_id,
                    alert_id=a.id,
                )
            )

        # Sort all events chronologically descending and trim to limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
