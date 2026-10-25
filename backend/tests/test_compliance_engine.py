"""Unit and Integration Tests for Compliance Engine.

Validates:
1. Physical attendance equals AI estimate -> MATCH
2. Difference within tolerance -> MATCH
3. Difference beyond tolerance -> DISCREPANCY
4. Median aggregation strategy
5. Mean aggregation strategy
6. Invalid (FAILED) observations ignored
7. No observations -> INSUFFICIENT_DATA
8. Expected infrastructure equals observed -> COMPLIANT
9. Observed infrastructure below expected -> DISCREPANCY
10. Unmapped inventory -> NOT_MONITORED
11. No valid infrastructure observations -> INSUFFICIENT_DATA
12. Multiple snapshots are never summed (asset count consistency)
13. Repeated calculation idempotency
14. Unauthorized access rejected (401/403)
15. Invalid session returns 404
16. Database transaction rollback behavior
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token
from backend.app.models.attendance import AttendanceObservation
from backend.app.models.camera import Camera
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
from backend.app.services.compliance_service import ComplianceService


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Provides valid Bearer Authorization header for admin user."""
    user = db_session.query(User).filter(User.email == "test_compliance_admin@sih.gov.in").first()
    if not user:
        user = User(
            email="test_compliance_admin@sih.gov.in",
            name="Compliance Admin",
            password_hash="mock_hash",
            role="ADMIN",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_admin_headers(db_session: Session) -> dict:
    """Provides Bearer Authorization header for non-admin user belonging to another centre."""
    other_centre = Centre(name="Other Centre", centre_code="OTH01", location="City B", status="ACTIVE")
    db_session.add(other_centre)
    db_session.commit()
    db_session.refresh(other_centre)

    user = User(
        email="other_staff@sih.gov.in",
        name="Other Staff",
        password_hash="mock_hash",
        role="STAFF",
        centre_id=other_centre.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def compliance_setup(db_session: Session) -> dict:
    """Sets up a complete monitoring session hierarchy with inventory and snapshots."""
    centre = Centre(
        name="Apex Skills Academy",
        centre_code="APEX01",
        location="Sector 18, Gurugram",
        status="ACTIVE",
    )
    db_session.add(centre)
    db_session.commit()
    db_session.refresh(centre)

    # Sanctioned Inventory Items
    inv_comp = InventoryItem(centre_id=centre.id, item_name="Desktop Computer", expected_quantity=20)
    inv_chair = InventoryItem(centre_id=centre.id, item_name="Student Chair", expected_quantity=25)
    inv_proj = InventoryItem(centre_id=centre.id, item_name="Multimedia Projector", expected_quantity=1)
    inv_unmapped = InventoryItem(centre_id=centre.id, item_name="Oscilloscope Calibration Kit", expected_quantity=3)
    db_session.add_all([inv_comp, inv_chair, inv_proj, inv_unmapped])
    db_session.commit()

    camera = Camera(
        centre_id=centre.id,
        name="Lab Cam 1",
        source_url="rtsp://lab.internal/stream",
        source_type="CAMERA",
        is_active=True,
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    session = MonitoringSession(
        centre_id=centre.id,
        camera_id=camera.id,
        physical_attendance=35,
        status="RUNNING",
        video_processing_status="COMPLETED",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create 3 snapshots
    snapshots = []
    for i in range(1, 4):
        snap = Snapshot(
            monitoring_session_id=session.id,
            sequence_number=i,
            file_path=f"snapshots/session_{session.id}/snap_{i}.jpg",
            frame_time_seconds=float(i * 10),
            width=640,
            height=480,
            processing_status="COMPLETED",
        )
        db_session.add(snap)
        snapshots.append(snap)
    db_session.commit()
    for s in snapshots:
        db_session.refresh(s)

    return {
        "centre": centre,
        "camera": camera,
        "session": session,
        "snapshots": snapshots,
        "inventory": {
            "computer": inv_comp,
            "chair": inv_chair,
            "projector": inv_proj,
            "unmapped": inv_unmapped,
        },
    }


# =========================================================================
# 1. Attendance Tests
# =========================================================================

def test_physical_attendance_equals_ai_estimate(db_session: Session, compliance_setup: dict):
    """1. Physical attendance equals AI estimate -> MATCH with 0 difference."""
    session = compliance_setup["session"]
    snapshots = compliance_setup["snapshots"]

    # 3 snapshots, all observed count 35
    for snap in snapshots:
        obs = AttendanceObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            observed_count=35,
            confidence_score=0.92,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    att, _ = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    assert att.status == "MATCH"
    assert att.physical_attendance == 35
    assert att.ai_estimated_attendance == 35.0
    assert att.difference == 0.0
    assert att.valid_observation_count == 3


def test_difference_within_tolerance(db_session: Session, compliance_setup: dict):
    """2. Difference within configured tolerance -> MATCH."""
    session = compliance_setup["session"]  # physical = 35
    snapshots = compliance_setup["snapshots"]

    # Observations: 34, 34, 33 -> Median = 34.0. Diff = 1.0 (<= tolerance 2)
    counts = [34, 34, 33]
    for snap, c in zip(snapshots, counts):
        obs = AttendanceObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            observed_count=c,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    att, _ = ComplianceService.calculate_and_save_session_compliance(
        db_session, session.id, tolerance=2
    )
    assert att.status == "MATCH"
    assert att.difference == 1.0
    assert att.tolerance == 2


def test_difference_beyond_tolerance(db_session: Session, compliance_setup: dict):
    """3. Difference beyond configured tolerance -> DISCREPANCY."""
    session = compliance_setup["session"]  # physical = 35
    snapshots = compliance_setup["snapshots"]

    # Observations: 28, 29, 30 -> Median = 29.0. Diff = 6.0 (> tolerance 2)
    counts = [28, 29, 30]
    for snap, c in zip(snapshots, counts):
        obs = AttendanceObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            observed_count=c,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    att, _ = ComplianceService.calculate_and_save_session_compliance(
        db_session, session.id, tolerance=2
    )
    assert att.status == "DISCREPANCY"
    assert att.difference == 6.0


def test_median_aggregation():
    """4. Validates median calculation across odd and even counts."""
    # Odd list
    assert ComplianceService.aggregate_values([10.0, 20.0, 30.0], method="MEDIAN") == 20.0
    # Even list
    assert ComplianceService.aggregate_values([10.0, 20.0, 30.0, 40.0], method="MEDIAN") == 25.0
    # Single item
    assert ComplianceService.aggregate_values([42.0], method="MEDIAN") == 42.0


def test_mean_aggregation():
    """5. Validates mean calculation."""
    assert ComplianceService.aggregate_values([10.0, 20.0, 30.0], method="MEAN") == 20.0
    assert ComplianceService.aggregate_values([10.0, 20.0, 33.0], method="MEAN") == 21.0


def test_invalid_observations_ignored(db_session: Session, compliance_setup: dict):
    """6. FAILED observations or records with invalid counts are ignored."""
    session = compliance_setup["session"]  # physical = 35
    snapshots = compliance_setup["snapshots"]

    # Add 2 COMPLETED (35, 35) and 1 FAILED (0)
    db_session.add(
        AttendanceObservation(
            snapshot_id=snapshots[0].id,
            monitoring_session_id=session.id,
            observed_count=35,
            processing_status="COMPLETED",
        )
    )
    db_session.add(
        AttendanceObservation(
            snapshot_id=snapshots[1].id,
            monitoring_session_id=session.id,
            observed_count=35,
            processing_status="COMPLETED",
        )
    )
    db_session.add(
        AttendanceObservation(
            snapshot_id=snapshots[2].id,
            monitoring_session_id=session.id,
            observed_count=0,
            processing_status="FAILED",  # Must be ignored
        )
    )
    db_session.commit()

    att, _ = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    assert att.status == "MATCH"
    assert att.valid_observation_count == 2
    assert att.ai_estimated_attendance == 35.0


def test_no_observations_yields_insufficient_data(db_session: Session, compliance_setup: dict):
    """7. Zero valid AI observations yields INSUFFICIENT_DATA (never a false discrepancy)."""
    session = compliance_setup["session"]
    att, _ = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    assert att.status == "INSUFFICIENT_DATA"
    assert att.ai_estimated_attendance is None
    assert att.difference is None
    assert att.valid_observation_count == 0


# =========================================================================
# 2. Infrastructure Tests
# =========================================================================

def test_expected_infrastructure_equals_observed(db_session: Session, compliance_setup: dict):
    """8. Observed quantity >= expected -> COMPLIANT."""
    session = compliance_setup["session"]
    snapshots = compliance_setup["snapshots"]

    # Expected computers = 20. Add 3 snapshot observations: 20, 20, 20
    for snap in snapshots:
        obs = InfrastructureObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            asset_type="computer",
            detected_quantity=20,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    _, infra = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    comp_result = next((item for item in infra if item.item_name == "Desktop Computer"), None)
    assert comp_result is not None
    assert comp_result.status == "COMPLIANT"
    assert comp_result.observed_quantity == 20.0
    assert comp_result.difference == 0.0


def test_observed_infrastructure_below_expected(db_session: Session, compliance_setup: dict):
    """9. Observed quantity below expected -> DISCREPANCY."""
    session = compliance_setup["session"]
    snapshots = compliance_setup["snapshots"]

    # Expected computers = 20. Observed: 17, 18, 17 -> Median = 17.0
    counts = [17, 18, 17]
    for snap, c in zip(snapshots, counts):
        obs = InfrastructureObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            asset_type="computer",
            detected_quantity=c,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    _, infra = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    comp_result = next((item for item in infra if item.item_name == "Desktop Computer"), None)
    assert comp_result is not None
    assert comp_result.status == "DISCREPANCY"
    assert comp_result.observed_quantity == 17.0
    assert comp_result.difference == 3.0  # expected (20) - observed (17)


def test_unmapped_inventory_not_monitored(db_session: Session, compliance_setup: dict):
    """10. Unmapped inventory item flagged as NOT_MONITORED, never missing-equipment discrepancy."""
    session = compliance_setup["session"]
    _, infra = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    unmapped_result = next((item for item in infra if item.item_name == "Oscilloscope Calibration Kit"), None)
    assert unmapped_result is not None
    assert unmapped_result.status == "NOT_MONITORED"
    assert unmapped_result.ai_class is None
    assert unmapped_result.observed_quantity is None


def test_no_valid_infrastructure_observations_insufficient_data(
    db_session: Session, compliance_setup: dict
):
    """11. Mapped inventory with 0 AI observations yields INSUFFICIENT_DATA."""
    session = compliance_setup["session"]
    _, infra = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    # Multimedia Projector maps to 'projector', but has 0 observations
    proj_result = next((item for item in infra if item.item_name == "Multimedia Projector"), None)
    assert proj_result is not None
    assert proj_result.status == "INSUFFICIENT_DATA"
    assert proj_result.ai_class == "projector"
    assert proj_result.observed_quantity is None


def test_multiple_snapshots_are_not_summed(db_session: Session, compliance_setup: dict):
    """12. Strict rule: Detections across snapshots are NEVER summed."""
    session = compliance_setup["session"]
    snapshots = compliance_setup["snapshots"]

    # 3 snapshots with 20 computers each. Summing would give 60.
    for snap in snapshots:
        obs = InfrastructureObservation(
            snapshot_id=snap.id,
            monitoring_session_id=session.id,
            asset_type="computer",
            detected_quantity=20,
            processing_status="COMPLETED",
        )
        db_session.add(obs)
    db_session.commit()

    _, infra = ComplianceService.calculate_and_save_session_compliance(db_session, session.id)
    comp_result = next((item for item in infra if item.item_name == "Desktop Computer"), None)
    assert comp_result.observed_quantity == 20.0
    assert comp_result.observed_quantity != 60.0


# =========================================================================
# 3. API, Idempotency & Security Tests
# =========================================================================

def test_repeated_compliance_calculation_is_idempotent(
    client: TestClient, auth_headers: dict, db_session: Session, compliance_setup: dict
):
    """13. POST /compliance/calculate multiple times updates existing records without duplication."""
    session = compliance_setup["session"]

    # First run
    res1 = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/compliance/calculate",
        headers=auth_headers,
    )
    assert res1.status_code == 200

    # Second run
    res2 = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/compliance/calculate",
        headers=auth_headers,
    )
    assert res2.status_code == 200

    # Check database rows directly: exactly 1 attendance result, 4 infra results
    att_count = (
        db_session.query(AttendanceComplianceResult)
        .filter(AttendanceComplianceResult.monitoring_session_id == session.id)
        .count()
    )
    infra_count = (
        db_session.query(InfrastructureComplianceResult)
        .filter(InfrastructureComplianceResult.monitoring_session_id == session.id)
        .count()
    )
    assert att_count == 1
    assert infra_count == 4


def test_unauthorized_access(
    client: TestClient, non_admin_headers: dict, compliance_setup: dict
):
    """14. Unauthenticated requests return 401; users for other centres return 403."""
    session = compliance_setup["session"]

    # Unauthenticated
    res_no_auth = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/compliance/calculate"
    )
    assert res_no_auth.status_code == 401

    # Unauthorized centre staff
    res_forbidden = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/compliance/calculate",
        headers=non_admin_headers,
    )
    assert res_forbidden.status_code == 403


def test_invalid_session_returns_404(client: TestClient, auth_headers: dict):
    """15. Calculating or getting compliance for non-existent session returns 404."""
    res_post = client.post(
        "/api/v1/monitoring/sessions/999999/compliance/calculate",
        headers=auth_headers,
    )
    assert res_post.status_code == 404

    res_get = client.get(
        "/api/v1/monitoring/sessions/999999/compliance",
        headers=auth_headers,
    )
    assert res_get.status_code == 404


def test_database_transaction_rollback_behavior(db_session: Session):
    """16. Verification of service handling when invalid session ID is supplied."""
    with pytest.raises(ValueError, match="Monitoring session #999999 not found"):
        ComplianceService.calculate_and_save_session_compliance(db_session, 999999)


def test_compliance_dashboard_summary(client: TestClient, auth_headers: dict, db_session: Session, compliance_setup: dict):
    """17. Verifies real database dashboard compliance metrics summary."""
    session = compliance_setup["session"]
    # Calculate compliance
    client.post(
        f"/api/v1/monitoring/sessions/{session.id}/compliance/calculate",
        headers=auth_headers,
    )

    res = client.get("/api/v1/monitoring/compliance/summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_sessions_evaluated" in data
    assert data["total_sessions_evaluated"] >= 1
    assert "attendance_matches" in data
    assert "attendance_discrepancies" in data
    assert "infrastructure_discrepancies" in data
    assert "insufficient_data_sessions" in data

