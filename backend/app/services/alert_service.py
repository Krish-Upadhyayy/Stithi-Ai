"""Compliance Alert and Human Review Service.

Implements the complete alert lifecycle:
1. Deterministic alert creation from persisted Compliance Engine discrepancies (DISCREPANCY status only).
2. Automatic attachment of supporting snapshot evidence from CCTV frames.
3. Human Review Workflow:
     PENDING -> VERIFIED
     PENDING -> FALSE_POSITIVE (requires justification comment)
   (Once finalized, review status cannot be reset or overwritten).
4. Centre-level data isolation and role-based review authorization.
5. Strict anti-defamation & privacy constraints:
   - Terminology: 'attendance discrepancy' or 'infrastructure discrepancy'.
   - Zero claims of fraud, criminality, or mechanical equipment failure.
   - Zero student identity tracking.
"""

from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.alert import Alert, AlertEvidence
from backend.app.models.attendance import AttendanceObservation
from backend.app.models.centre import Centre
from backend.app.models.compliance import (
    AttendanceComplianceResult,
    InfrastructureComplianceResult,
)
from backend.app.models.infrastructure import InfrastructureObservation
from backend.app.models.inventory import InventoryItem
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.user import User

logger = logging.getLogger(__name__)


class AlertService:
    """Manages compliance discrepancy alert creation, evidence linkage, and human review."""

    @staticmethod
    def calculate_attendance_severity(diff: float) -> str:
        """Determines attendance alert severity using configurable prototype thresholds."""
        val = abs(diff)
        if val <= settings.ALERT_ATTENDANCE_LOW_THRESHOLD:
            return "LOW"
        if val <= settings.ALERT_ATTENDANCE_MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def calculate_infrastructure_severity(diff: float) -> str:
        """Determines infrastructure alert severity using configurable prototype thresholds."""
        val = abs(diff)
        if val <= settings.ALERT_INFRASTRUCTURE_LOW_THRESHOLD:
            return "LOW"
        if val <= settings.ALERT_INFRASTRUCTURE_MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "HIGH"

    @classmethod
    def generate_session_alerts(
        cls, db: Session, session_id: int
    ) -> Tuple[List[Alert], int, int]:
        """Scans persisted compliance results for a session and idempotently creates alerts for discrepancies.
        
        Returns: (all_session_alerts, newly_created_count, existing_count)
        """
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise ValueError(f"Monitoring session #{session_id} not found.")

        created_count = 0
        existing_count = 0
        result_alerts: List[Alert] = []

        # -------------------------------------------------------------
        # 1. Attendance Compliance Alert
        # -------------------------------------------------------------
        att_compliance = (
            db.query(AttendanceComplianceResult)
            .filter(AttendanceComplianceResult.monitoring_session_id == session.id)
            .first()
        )

        # Only create alert if compliance evaluation yielded DISCREPANCY
        if att_compliance and att_compliance.status == "DISCREPANCY":
            existing_att_alert = (
                db.query(Alert)
                .filter(
                    Alert.monitoring_session_id == session.id,
                    Alert.alert_type == "ATTENDANCE_DISCREPANCY",
                )
                .first()
            )

            diff = att_compliance.difference if att_compliance.difference is not None else 0.0
            ai_est = att_compliance.ai_estimated_attendance if att_compliance.ai_estimated_attendance is not None else 0.0

            if existing_att_alert:
                # Idempotency: Preserve existing alert, do NOT reset VERIFIED or FALSE_POSITIVE back to PENDING
                result_alerts.append(existing_att_alert)
                existing_count += 1
            else:
                severity = cls.calculate_attendance_severity(diff)
                description = (
                    f"Physical attendance was recorded as {att_compliance.physical_attendance}, "
                    f"while the AI estimated {ai_est:.1f} across {att_compliance.valid_observation_count} "
                    f"valid snapshots. The configured tolerance was {att_compliance.tolerance}."
                )

                new_alert = Alert(
                    centre_id=session.centre_id,
                    monitoring_session_id=session.id,
                    session_id=session.id,
                    compliance_result_id=att_compliance.id,
                    alert_type="ATTENDANCE_DISCREPANCY",
                    severity=severity,
                    title="Potential Attendance Discrepancy Detected",
                    description=description,
                    expected_value=float(att_compliance.physical_attendance),
                    observed_value=float(ai_est),
                    detected_value=float(ai_est),
                    difference=float(diff),
                    status="PENDING",
                )
                db.add(new_alert)
                db.flush()

                # Attach supporting attendance snapshot evidence
                cls._attach_attendance_evidence(db, new_alert, session.id)
                result_alerts.append(new_alert)
                created_count += 1

        # -------------------------------------------------------------
        # 2. Infrastructure Compliance Alerts
        # -------------------------------------------------------------
        infra_compliances = (
            db.query(InfrastructureComplianceResult)
            .filter(InfrastructureComplianceResult.monitoring_session_id == session.id)
            .all()
        )

        for infra_comp in infra_compliances:
            # Strictly create alerts only when status == DISCREPANCY
            # (Never for COMPLIANT, NOT_MONITORED, or INSUFFICIENT_DATA)
            if infra_comp.status != "DISCREPANCY":
                continue

            existing_infra_alert = (
                db.query(Alert)
                .filter(
                    Alert.monitoring_session_id == session.id,
                    Alert.alert_type == "INFRASTRUCTURE_DISCREPANCY",
                    Alert.inventory_item_id == infra_comp.inventory_item_id,
                )
                .first()
            )

            diff = infra_comp.difference if infra_comp.difference is not None else 0.0
            obs_qty = infra_comp.observed_quantity if infra_comp.observed_quantity is not None else 0.0

            if existing_infra_alert:
                # Idempotency: Preserve finalized human review state
                result_alerts.append(existing_infra_alert)
                existing_count += 1
            else:
                severity = cls.calculate_infrastructure_severity(diff)
                description = (
                    f"{obs_qty:.1f} {infra_comp.item_name} were visually detected against an expected quantity "
                    f"of {infra_comp.expected_quantity} across {infra_comp.valid_observation_count} valid snapshots."
                )

                new_alert = Alert(
                    centre_id=session.centre_id,
                    monitoring_session_id=session.id,
                    session_id=session.id,
                    compliance_result_id=infra_comp.id,
                    inventory_item_id=infra_comp.inventory_item_id,
                    alert_type="INFRASTRUCTURE_DISCREPANCY",
                    severity=severity,
                    title=f"Potential Infrastructure Discrepancy: {infra_comp.item_name}",
                    description=description,
                    expected_value=float(infra_comp.expected_quantity),
                    observed_value=float(obs_qty),
                    detected_value=float(obs_qty),
                    difference=float(diff),
                    status="PENDING",
                )
                db.add(new_alert)
                db.flush()

                # Attach supporting infrastructure snapshot evidence
                cls._attach_infrastructure_evidence(db, new_alert, session.id, infra_comp.ai_class)
                result_alerts.append(new_alert)
                created_count += 1

        db.commit()
        for a in result_alerts:
            db.refresh(a)

        logger.info(
            f"Alert generation for Session #{session_id}: created={created_count}, existing={existing_count}"
        )
        return result_alerts, created_count, existing_count

    @classmethod
    def _attach_attendance_evidence(cls, db: Session, alert: Alert, session_id: int):
        """Attaches relevant attendance snapshots as evidence records."""
        valid_obs = (
            db.query(AttendanceObservation)
            .filter(
                AttendanceObservation.monitoring_session_id == session_id,
                AttendanceObservation.processing_status == "COMPLETED",
            )
            .order_by(AttendanceObservation.id.asc())
            .all()
        )

        attached_snapshots = set()
        for obs in valid_obs:
            if obs.snapshot_id not in attached_snapshots:
                evidence = AlertEvidence(
                    alert_id=alert.id,
                    snapshot_id=obs.snapshot_id,
                    evidence_type="ATTENDANCE_SNAPSHOT",
                    observation_id=obs.id,
                )
                db.add(evidence)
                attached_snapshots.add(obs.snapshot_id)

    @classmethod
    def _attach_infrastructure_evidence(
        cls, db: Session, alert: Alert, session_id: int, ai_class: Optional[str]
    ):
        """Attaches relevant infrastructure snapshot evidence for the given asset class."""
        query = (
            db.query(InfrastructureObservation)
            .filter(
                InfrastructureObservation.monitoring_session_id == session_id,
                InfrastructureObservation.processing_status == "COMPLETED",
            )
        )
        if ai_class:
            query = query.filter(InfrastructureObservation.asset_type == ai_class.lower())

        valid_obs = query.order_by(InfrastructureObservation.id.asc()).all()

        attached_snapshots = set()
        for obs in valid_obs:
            if obs.snapshot_id not in attached_snapshots:
                evidence = AlertEvidence(
                    alert_id=alert.id,
                    snapshot_id=obs.snapshot_id,
                    evidence_type="INFRASTRUCTURE_SNAPSHOT",
                    observation_id=obs.id,
                )
                db.add(evidence)
                attached_snapshots.add(obs.snapshot_id)

        # Fallback: if no class-specific detections occurred, attach completed session snapshots for reviewer context
        if not attached_snapshots:
            session_snaps = (
                db.query(Snapshot)
                .filter(
                    Snapshot.monitoring_session_id == session_id,
                    Snapshot.processing_status == "COMPLETED",
                )
                .limit(3)
                .all()
            )
            for snap in session_snaps:
                evidence = AlertEvidence(
                    alert_id=alert.id,
                    snapshot_id=snap.id,
                    evidence_type="INFRASTRUCTURE_SNAPSHOT",
                    observation_id=None,
                )
                db.add(evidence)

    @staticmethod
    def review_alert(
        db: Session, alert_id: int, reviewer: User, target_status: str, comment: Optional[str]
    ) -> Alert:
        """Executes human review state transition on a pending alert with audit tracking."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert #{alert_id} not found.")

        # Centre authorization check
        if reviewer.role not in ("ADMIN", "REVIEWER") and reviewer.centre_id != alert.centre_id:
            raise PermissionError("You are not authorized to review alerts for this centre.")

        # Role control: only ADMIN or REVIEWER can finalize review decisions
        if reviewer.role not in ("ADMIN", "REVIEWER"):
            raise PermissionError("Only users with ADMIN or REVIEWER roles can review alerts.")

        clean_status = target_status.strip().upper()
        if clean_status not in ("VERIFIED", "FALSE_POSITIVE"):
            raise ValueError("Review status must be either 'VERIFIED' or 'FALSE_POSITIVE'.")

        # Status transition lock: once reviewed, cannot transition again or reset to PENDING
        if alert.status in ("VERIFIED", "FALSE_POSITIVE"):
            raise ValueError(
                f"Alert #{alert_id} has already been reviewed as '{alert.status}' and cannot be modified."
            )

        # Mandatory comment check for FALSE_POSITIVE
        if clean_status == "FALSE_POSITIVE":
            if not comment or not comment.strip():
                raise ValueError("Reviewer comment is mandatory when marking an alert as FALSE_POSITIVE.")

        alert.status = clean_status
        alert.reviewed_at = datetime.utcnow()
        alert.reviewed_by = reviewer.id
        alert.reviewer_comment = comment.strip() if comment else None

        db.commit()
        db.refresh(alert)
        logger.info(f"Alert #{alert_id} reviewed as '{clean_status}' by User #{reviewer.id} ({reviewer.email})")
        return alert

    @staticmethod
    def get_alerts(
        db: Session,
        user: Optional[User] = None,
        centre_id: Optional[int] = None,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        session_id: Optional[int] = None,
    ) -> List[Alert]:
        """Lists alerts enforcing centre-level authorization and user filters."""
        query = db.query(Alert)

        # Enforce centre-level data isolation
        if user and user.role not in ("ADMIN", "REVIEWER"):
            if user.centre_id:
                query = query.filter(Alert.centre_id == user.centre_id)
            else:
                return []

        if centre_id:
            query = query.filter(Alert.centre_id == centre_id)
        if status:
            query = query.filter(Alert.status == status.strip().upper())
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type.strip().upper())
        if severity:
            query = query.filter(Alert.severity == severity.strip().upper())
        if session_id:
            query = query.filter(
                (Alert.monitoring_session_id == session_id) | (Alert.session_id == session_id)
            )

        return query.order_by(Alert.created_at.desc()).all()

    @staticmethod
    def get_alert_by_id(db: Session, alert_id: int, user: Optional[User] = None) -> Alert:
        """Retrieves a single alert verifying access permissions."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert #{alert_id} not found.")

        if user and user.role not in ("ADMIN", "REVIEWER"):
            if user.centre_id != alert.centre_id:
                raise PermissionError("Access forbidden: you do not have permission for this centre's alerts.")

        return alert

    @staticmethod
    def get_summary_metrics(db: Session, user: Optional[User] = None) -> Dict[str, int]:
        """Retrieves real database summary counts of alerts by status and category."""
        base_query = db.query(Alert)
        if user and user.role not in ("ADMIN", "REVIEWER"):
            if user.centre_id:
                base_query = base_query.filter(Alert.centre_id == user.centre_id)
            else:
                return {
                    "total_alerts": 0,
                    "pending_alerts": 0,
                    "verified_alerts": 0,
                    "false_positive_alerts": 0,
                    "attendance_discrepancies": 0,
                    "infrastructure_discrepancies": 0,
                    "high_severity_alerts": 0,
                }

        total = base_query.count()
        pending = base_query.filter(Alert.status == "PENDING").count()
        verified = base_query.filter(Alert.status == "VERIFIED").count()
        false_positive = base_query.filter(Alert.status == "FALSE_POSITIVE").count()
        attendance = base_query.filter(Alert.alert_type == "ATTENDANCE_DISCREPANCY").count()
        infra = base_query.filter(Alert.alert_type == "INFRASTRUCTURE_DISCREPANCY").count()
        high_sev = base_query.filter(Alert.severity == "HIGH").count()

        return {
            "total_alerts": total,
            "pending_alerts": pending,
            "verified_alerts": verified,
            "false_positive_alerts": false_positive,
            "attendance_discrepancies": attendance,
            "infrastructure_discrepancies": infra,
            "high_severity_alerts": high_sev,
        }
