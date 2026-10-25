"""Compliance Engine Service.

Executes deterministic, robust compliance evaluation comparing:
1. Physical Attendance vs AI-estimated Attendance (Median / Mean aggregate across snapshots)
2. Sanctioned Centre Inventory vs AI-detected Infrastructure Presence

Core Architectural Principles:
- Multiple snapshots are NEVER summed; robust aggregation (Default: MEDIAN) is used to prevent duplicate counting.
- Absence of AI observations yields 'INSUFFICIENT_DATA' rather than assuming a discrepancy.
- Unmapped inventory items yield 'NOT_MONITORED' and never trigger missing equipment alarms.
- Visual AI assesses apparent visual presence only — zero claim of mechanical or electrical operability.
- Idempotent calculations safely replace prior compliance outputs for the session.
"""

from datetime import datetime
import logging
import statistics
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.attendance import AttendanceObservation
from backend.app.models.compliance import (
    AttendanceComplianceResult,
    InfrastructureComplianceResult,
)
from backend.app.models.infrastructure import InfrastructureObservation
from backend.app.models.inventory import InventoryItem
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.pipelines.infrastructure.mapping import default_mapper

logger = logging.getLogger(__name__)


class ComplianceService:
    """Orchestrates Attendance and Infrastructure compliance checks for Monitoring Sessions."""

    @staticmethod
    def aggregate_values(values: List[float], method: str = "MEDIAN") -> float:
        """Aggregates observation counts across snapshots using a robust statistical strategy.
        
        Strict Rule: Never sum observations across snapshots to avoid duplicate asset or person counts.
        """
        if not values:
            raise ValueError("Cannot aggregate empty observation list.")
        
        normalized_method = (method or "MEDIAN").strip().upper()
        if normalized_method == "MEAN":
            return float(statistics.mean(values))
        # Default strategy: MEDIAN
        return float(statistics.median(values))

    @classmethod
    def calculate_attendance_compliance(
        cls,
        db: Session,
        session: MonitoringSession,
        tolerance: Optional[int] = None,
        method: Optional[str] = None,
        total_snapshots: int = 0,
    ) -> AttendanceComplianceResult:
        """Evaluates physical headcount against AI face/presence detection observations."""
        tol = tolerance if tolerance is not None else settings.COMPLIANCE_ATTENDANCE_TOLERANCE
        agg_method = (method or settings.COMPLIANCE_AGGREGATION_METHOD).strip().upper()

        # Retrieve valid, successfully processed attendance observations for this session
        valid_observations = (
            db.query(AttendanceObservation)
            .filter(
                AttendanceObservation.monitoring_session_id == session.id,
                AttendanceObservation.processing_status == "COMPLETED",
            )
            .all()
        )

        counts = [
            float(obs.observed_count)
            for obs in valid_observations
            if obs.observed_count is not None and obs.observed_count >= 0
        ]

        # Case: Insufficient AI data
        if not counts:
            return AttendanceComplianceResult(
                monitoring_session_id=session.id,
                physical_attendance=session.physical_attendance,
                ai_estimated_attendance=None,
                difference=None,
                tolerance=tol,
                aggregation_method=agg_method,
                valid_observation_count=0,
                total_snapshots_considered=total_snapshots,
                status="INSUFFICIENT_DATA",
                calculated_at=datetime.utcnow(),
            )

        ai_estimate = cls.aggregate_values(counts, method=agg_method)
        diff = abs(float(session.physical_attendance) - ai_estimate)
        status = "MATCH" if diff <= tol else "DISCREPANCY"

        return AttendanceComplianceResult(
            monitoring_session_id=session.id,
            physical_attendance=session.physical_attendance,
            ai_estimated_attendance=ai_estimate,
            difference=diff,
            tolerance=tol,
            aggregation_method=agg_method,
            valid_observation_count=len(counts),
            total_snapshots_considered=total_snapshots,
            status=status,
            calculated_at=datetime.utcnow(),
        )

    @classmethod
    def calculate_infrastructure_compliance(
        cls,
        db: Session,
        session: MonitoringSession,
        method: Optional[str] = None,
        total_snapshots: int = 0,
    ) -> List[InfrastructureComplianceResult]:
        """Evaluates sanctioned inventory expectations against visible AI asset detections."""
        agg_method = (method or settings.COMPLIANCE_AGGREGATION_METHOD).strip().upper()

        # Query sanctioned inventory items for the centre
        inventory_items = (
            db.query(InventoryItem)
            .filter(InventoryItem.centre_id == session.centre_id)
            .all()
        )

        # Pre-query all valid infrastructure observations for this session grouped by class
        valid_observations = (
            db.query(InfrastructureObservation)
            .filter(
                InfrastructureObservation.monitoring_session_id == session.id,
                InfrastructureObservation.processing_status == "COMPLETED",
            )
            .all()
        )

        # Group detected quantities by normalized asset_type
        obs_by_class: Dict[str, List[float]] = {}
        for obs in valid_observations:
            if obs.detected_quantity is not None and obs.detected_quantity >= 0:
                key = obs.asset_type.strip().lower()
                obs_by_class.setdefault(key, []).append(float(obs.detected_quantity))

        results: List[InfrastructureComplianceResult] = []

        for item in inventory_items:
            ai_class = default_mapper.map_inventory_to_class(item.item_name)

            # Case: Unmapped inventory item
            if not ai_class:
                results.append(
                    InfrastructureComplianceResult(
                        monitoring_session_id=session.id,
                        inventory_item_id=item.id,
                        item_name=item.item_name,
                        ai_class=None,
                        expected_quantity=item.expected_quantity,
                        observed_quantity=None,
                        difference=None,
                        aggregation_method=agg_method,
                        valid_observation_count=0,
                        total_snapshots_considered=total_snapshots,
                        status="NOT_MONITORED",
                        calculated_at=datetime.utcnow(),
                    )
                )
                continue

            # Monitored item: Check observation availability
            class_counts = obs_by_class.get(ai_class.lower(), [])
            if not class_counts:
                results.append(
                    InfrastructureComplianceResult(
                        monitoring_session_id=session.id,
                        inventory_item_id=item.id,
                        item_name=item.item_name,
                        ai_class=ai_class,
                        expected_quantity=item.expected_quantity,
                        observed_quantity=None,
                        difference=None,
                        aggregation_method=agg_method,
                        valid_observation_count=0,
                        total_snapshots_considered=total_snapshots,
                        status="INSUFFICIENT_DATA",
                        calculated_at=datetime.utcnow(),
                    )
                )
                continue

            # Calculate robust aggregate observed quantity
            observed_qty = cls.aggregate_values(class_counts, method=agg_method)
            diff = float(item.expected_quantity) - observed_qty
            status = "COMPLIANT" if observed_qty >= float(item.expected_quantity) else "DISCREPANCY"

            results.append(
                InfrastructureComplianceResult(
                    monitoring_session_id=session.id,
                    inventory_item_id=item.id,
                    item_name=item.item_name,
                    ai_class=ai_class,
                    expected_quantity=item.expected_quantity,
                    observed_quantity=observed_qty,
                    difference=diff,
                    aggregation_method=agg_method,
                    valid_observation_count=len(class_counts),
                    total_snapshots_considered=total_snapshots,
                    status=status,
                    calculated_at=datetime.utcnow(),
                )
            )

        return results

    @classmethod
    def calculate_and_save_session_compliance(
        cls,
        db: Session,
        session_id: int,
        tolerance: Optional[int] = None,
        method: Optional[str] = None,
    ) -> Tuple[AttendanceComplianceResult, List[InfrastructureComplianceResult]]:
        """Idempotently executes compliance calculation and updates the database records."""
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise ValueError(f"Monitoring session #{session_id} not found.")

        # Count completed snapshots available for this session
        total_snapshots = (
            db.query(Snapshot)
            .filter(
                Snapshot.monitoring_session_id == session.id,
                Snapshot.processing_status == "COMPLETED",
            )
            .count()
        )

        attendance_result = cls.calculate_attendance_compliance(
            db, session, tolerance=tolerance, method=method, total_snapshots=total_snapshots
        )
        infra_results = cls.calculate_infrastructure_compliance(
            db, session, method=method, total_snapshots=total_snapshots
        )

        # Idempotent persistence: remove prior compliance calculations for this session
        db.query(AttendanceComplianceResult).filter(
            AttendanceComplianceResult.monitoring_session_id == session.id
        ).delete(synchronize_session=False)

        db.query(InfrastructureComplianceResult).filter(
            InfrastructureComplianceResult.monitoring_session_id == session.id
        ).delete(synchronize_session=False)

        db.add(attendance_result)
        for infra in infra_results:
            db.add(infra)

        db.commit()
        db.refresh(attendance_result)
        for infra in infra_results:
            db.refresh(infra)

        logger.info(
            f"Compliance calculated for Session #{session.id}: Attendance status={attendance_result.status}, "
            f"Infrastructure evaluated items={len(infra_results)}"
        )
        return attendance_result, infra_results

    @staticmethod
    def get_session_compliance(
        db: Session, session_id: int
    ) -> Tuple[Optional[AttendanceComplianceResult], List[InfrastructureComplianceResult]]:
        """Retrieves existing compliance records for a session."""
        att = (
            db.query(AttendanceComplianceResult)
            .filter(AttendanceComplianceResult.monitoring_session_id == session_id)
            .first()
        )
        infra = (
            db.query(InfrastructureComplianceResult)
            .filter(InfrastructureComplianceResult.monitoring_session_id == session_id)
            .order_by(InfrastructureComplianceResult.item_name.asc())
            .all()
        )
        return att, infra

    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict:
        """Retrieves real database summary counts of evaluated sessions and compliance states."""
        total_sessions = (
            db.query(AttendanceComplianceResult.monitoring_session_id)
            .distinct()
            .count()
        )
        att_matches = (
            db.query(AttendanceComplianceResult)
            .filter(AttendanceComplianceResult.status == "MATCH")
            .count()
        )
        att_discrepancies = (
            db.query(AttendanceComplianceResult)
            .filter(AttendanceComplianceResult.status == "DISCREPANCY")
            .count()
        )
        infra_discrepancies = (
            db.query(InfrastructureComplianceResult)
            .filter(InfrastructureComplianceResult.status == "DISCREPANCY")
            .count()
        )
        insufficient_data = (
            db.query(AttendanceComplianceResult)
            .filter(AttendanceComplianceResult.status == "INSUFFICIENT_DATA")
            .count()
        )
        latest_calc = (
            db.query(func.max(AttendanceComplianceResult.calculated_at))
            .scalar()
        )

        return {
            "total_sessions_evaluated": total_sessions,
            "attendance_matches": att_matches,
            "attendance_discrepancies": att_discrepancies,
            "infrastructure_discrepancies": infra_discrepancies,
            "insufficient_data_sessions": insufficient_data,
            "last_calculated_at": latest_calc,
        }
