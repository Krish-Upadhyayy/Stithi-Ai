"""Comprehensive tests for Alert Generation, Evidence Attachment, and Human Review.

Validates all 20 requirements specified in Prompt 13:
1. Attendance discrepancy creates alert.
2. Attendance MATCH does not create alert.
3. Attendance INSUFFICIENT_DATA does not create alert.
4. Infrastructure discrepancy creates alert.
5. Infrastructure COMPLIANT does not create alert.
6. Infrastructure NOT_MONITORED does not create alert.
7. Infrastructure INSUFFICIENT_DATA does not create alert.
8. Duplicate generation does not create duplicate alerts.
9. Existing VERIFIED alert remains VERIFIED.
10. Existing FALSE_POSITIVE alert remains FALSE_POSITIVE.
11. PENDING -> VERIFIED works.
12. PENDING -> FALSE_POSITIVE works.
13. Invalid status transition is rejected.
14. FALSE_POSITIVE requires reviewer comment.
15. Reviewer identity comes from authenticated user.
16. Unauthorized users cannot review.
17. Unauthorized users cannot access evidence.
18. Alert evidence references real snapshots.
19. Invalid alert ID returns appropriate error.
20. Centre-level authorization works.
"""

from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token
from backend.app.models.alert import Alert, AlertEvidence
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
from backend.app.services.alert_service import AlertService


@pytest.fixture
def test_environment(db_session: Session):
    """Sets up centres, users with roles, session, snapshots, and compliance results."""
    # Centre A and Centre B
    centre_a = Centre(name="Centre Alpha", centre_code="C-ALPHA", location="New Delhi", status="ACTIVE")
    centre_b = Centre(name="Centre Beta", centre_code="C-BETA", location="Mumbai", status="ACTIVE")
    db_session.add_all([centre_a, centre_b])
    db_session.commit()
    db_session.refresh(centre_a)
    db_session.refresh(centre_b)

    # Users
    admin = User(email="admin@alerts.gov.in", name="Admin User", password_hash="hash", role="ADMIN")
    reviewer = User(email="reviewer@alerts.gov.in", name="Reviewer User", password_hash="hash", role="REVIEWER")
    staff_a = User(email="staff_a@alerts.gov.in", name="Staff A", password_hash="hash", role="STAFF", centre_id=centre_a.id)
    staff_b = User(email="staff_b@alerts.gov.in", name="Staff B", password_hash="hash", role="STAFF", centre_id=centre_b.id)
    db_session.add_all([admin, reviewer, staff_a, staff_b])
    db_session.commit()
    for u in (admin, reviewer, staff_a, staff_b):
        db_session.refresh(u)

    # Camera & Session in Centre A
    camera = Camera(name="Lab Camera", centre_id=centre_a.id, source_url="rtsp://test", source_type="CAMERA", is_active=True)
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    session = MonitoringSession(
        centre_id=centre_a.id,
        camera_id=camera.id,
        physical_attendance=35,
        status="RUNNING",
        video_processing_status="COMPLETED",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Snapshots
    snap1 = Snapshot(monitoring_session_id=session.id, sequence_number=1, file_path="snap1.jpg", width=320, height=240, processing_status="COMPLETED")
    snap2 = Snapshot(monitoring_session_id=session.id, sequence_number=2, file_path="snap2.jpg", width=320, height=240, processing_status="COMPLETED")
    db_session.add_all([snap1, snap2])
    db_session.commit()
    db_session.refresh(snap1)
    db_session.refresh(snap2)

    # Observations
    att_obs1 = AttendanceObservation(snapshot_id=snap1.id, monitoring_session_id=session.id, observed_count=28, processing_status="COMPLETED")
    att_obs2 = AttendanceObservation(snapshot_id=snap2.id, monitoring_session_id=session.id, observed_count=28, processing_status="COMPLETED")
    db_session.add_all([att_obs1, att_obs2])

    inv_comp = InventoryItem(centre_id=centre_a.id, item_name="Desktop Computer", expected_quantity=20)
    inv_chair = InventoryItem(centre_id=centre_a.id, item_name="Student Chair", expected_quantity=25)
    db_session.add_all([inv_comp, inv_chair])
    db_session.commit()
    db_session.refresh(inv_comp)
    db_session.refresh(inv_chair)

    infra_obs1 = InfrastructureObservation(
        snapshot_id=snap1.id, monitoring_session_id=session.id, asset_type="computer", detected_quantity=17, processing_status="COMPLETED"
    )
    infra_obs2 = InfrastructureObservation(
        snapshot_id=snap2.id, monitoring_session_id=session.id, asset_type="chair", detected_quantity=25, processing_status="COMPLETED"
    )
    db_session.add_all([infra_obs1, infra_obs2])
    db_session.commit()

    return {
        "centre_a": centre_a,
        "centre_b": centre_b,
        "admin": admin,
        "reviewer": reviewer,
        "staff_a": staff_a,
        "staff_b": staff_b,
        "session": session,
        "snapshots": [snap1, snap2],
        "inventory": {"computer": inv_comp, "chair": inv_chair},
    }


def make_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# 1. Alert Creation & Rules Tests
# =========================================================================

def test_attendance_discrepancy_creates_alert(db_session: Session, test_environment: dict):
    """1. Attendance DISCREPANCY creates an alert with supporting evidence."""
    session = test_environment["session"]
    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=28.0,
        difference=7.0,
        tolerance=2,
        valid_observation_count=2,
        total_snapshots_considered=2,
        status="DISCREPANCY",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    alerts, created, existing = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 1
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_type == "ATTENDANCE_DISCREPANCY"
    assert alert.status == "PENDING"
    assert alert.difference == 7.0
    assert len(alert.evidence) == 2


def test_attendance_match_does_not_create_alert(db_session: Session, test_environment: dict):
    """2. Attendance MATCH does not create any alert."""
    session = test_environment["session"]
    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=34.0,
        difference=1.0,
        tolerance=2,
        status="MATCH",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert len(alerts) == 0


def test_attendance_insufficient_data_does_not_create_alert(db_session: Session, test_environment: dict):
    """3. Attendance INSUFFICIENT_DATA does not create an alert."""
    session = test_environment["session"]
    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=None,
        difference=None,
        status="INSUFFICIENT_DATA",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert len(alerts) == 0


def test_infrastructure_discrepancy_creates_alert(db_session: Session, test_environment: dict):
    """4. Infrastructure DISCREPANCY creates an alert with supporting evidence."""
    session = test_environment["session"]
    inv_comp = test_environment["inventory"]["computer"]

    infra_comp = InfrastructureComplianceResult(
        monitoring_session_id=session.id,
        inventory_item_id=inv_comp.id,
        item_name="Desktop Computer",
        ai_class="computer",
        expected_quantity=20,
        observed_quantity=17.0,
        difference=3.0,
        valid_observation_count=1,
        total_snapshots_considered=2,
        status="DISCREPANCY",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(infra_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 1
    alert = alerts[0]
    assert alert.alert_type == "INFRASTRUCTURE_DISCREPANCY"
    assert alert.status == "PENDING"
    assert alert.inventory_item_id == inv_comp.id
    assert len(alert.evidence) >= 1


def test_infrastructure_compliant_does_not_create_alert(db_session: Session, test_environment: dict):
    """5. Infrastructure COMPLIANT does not create an alert."""
    session = test_environment["session"]
    inv_chair = test_environment["inventory"]["chair"]

    infra_comp = InfrastructureComplianceResult(
        monitoring_session_id=session.id,
        inventory_item_id=inv_chair.id,
        item_name="Student Chair",
        ai_class="chair",
        expected_quantity=25,
        observed_quantity=25.0,
        difference=0.0,
        status="COMPLIANT",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(infra_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert len(alerts) == 0


def test_infrastructure_not_monitored_does_not_create_alert(db_session: Session, test_environment: dict):
    """6. Unmapped inventory flagged NOT_MONITORED does not create an alert."""
    session = test_environment["session"]
    infra_comp = InfrastructureComplianceResult(
        monitoring_session_id=session.id,
        inventory_item_id=None,
        item_name="Soldering Iron Kit",
        ai_class=None,
        expected_quantity=5,
        observed_quantity=None,
        difference=None,
        status="NOT_MONITORED",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(infra_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert len(alerts) == 0


def test_infrastructure_insufficient_data_does_not_create_alert(db_session: Session, test_environment: dict):
    """7. Infrastructure INSUFFICIENT_DATA does not create an alert."""
    session = test_environment["session"]
    infra_comp = InfrastructureComplianceResult(
        monitoring_session_id=session.id,
        inventory_item_id=None,
        item_name="Projector",
        ai_class="projector",
        expected_quantity=1,
        observed_quantity=None,
        difference=None,
        status="INSUFFICIENT_DATA",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(infra_comp)
    db_session.commit()

    alerts, created, _ = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert len(alerts) == 0


def test_duplicate_generation_does_not_duplicate_alerts(db_session: Session, test_environment: dict):
    """8. Running alert generation multiple times is idempotent."""
    session = test_environment["session"]
    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=28.0,
        difference=7.0,
        tolerance=2,
        status="DISCREPANCY",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    # First run
    _, created1, existing1 = AlertService.generate_session_alerts(db_session, session.id)
    assert created1 == 1
    assert existing1 == 0

    # Second run
    _, created2, existing2 = AlertService.generate_session_alerts(db_session, session.id)
    assert created2 == 0
    assert existing2 == 1

    total_alerts = db_session.query(Alert).filter(Alert.monitoring_session_id == session.id).count()
    assert total_alerts == 1


def test_existing_verified_alert_remains_verified(db_session: Session, test_environment: dict):
    """9. Re-generating alerts preserves VERIFIED status and does not reset to PENDING."""
    session = test_environment["session"]
    admin = test_environment["admin"]

    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=28.0,
        difference=7.0,
        tolerance=2,
        status="DISCREPANCY",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    # Generate and verify
    alerts, _, _ = AlertService.generate_session_alerts(db_session, session.id)
    alert = alerts[0]
    AlertService.review_alert(db_session, alert.id, admin, "VERIFIED", "Discrepancy confirmed by admin.")

    # Re-generate alerts
    re_alerts, created, existing = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert existing == 1
    assert re_alerts[0].status == "VERIFIED"


def test_existing_false_positive_alert_remains_false_positive(db_session: Session, test_environment: dict):
    """10. Re-generating alerts preserves FALSE_POSITIVE status."""
    session = test_environment["session"]
    admin = test_environment["admin"]

    att_comp = AttendanceComplianceResult(
        monitoring_session_id=session.id,
        physical_attendance=35,
        ai_estimated_attendance=28.0,
        difference=7.0,
        tolerance=2,
        status="DISCREPANCY",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(att_comp)
    db_session.commit()

    alerts, _, _ = AlertService.generate_session_alerts(db_session, session.id)
    alert = alerts[0]
    AlertService.review_alert(db_session, alert.id, admin, "FALSE_POSITIVE", "Camera angle obscured room.")

    # Re-generate alerts
    re_alerts, created, existing = AlertService.generate_session_alerts(db_session, session.id)
    assert created == 0
    assert existing == 1
    assert re_alerts[0].status == "FALSE_POSITIVE"


# =========================================================================
# 2. Human Review Workflow Tests
# =========================================================================

def test_pending_to_verified_works(db_session: Session, test_environment: dict):
    """11. Reviewing alert PENDING -> VERIFIED updates status and audit fields."""
    session = test_environment["session"]
    reviewer = test_environment["reviewer"]

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        difference=5.0,
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    updated = AlertService.review_alert(db_session, alert.id, reviewer, "VERIFIED", "Reviewed CCTV footage.")
    assert updated.status == "VERIFIED"
    assert updated.reviewed_by == reviewer.id
    assert updated.reviewer_comment == "Reviewed CCTV footage."
    assert updated.reviewed_at is not None


def test_pending_to_false_positive_works(db_session: Session, test_environment: dict):
    """12. Reviewing alert PENDING -> FALSE_POSITIVE updates status with required comment."""
    session = test_environment["session"]
    reviewer = test_environment["reviewer"]

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        difference=5.0,
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    updated = AlertService.review_alert(db_session, alert.id, reviewer, "FALSE_POSITIVE", "Camera glare issue.")
    assert updated.status == "FALSE_POSITIVE"
    assert updated.reviewed_by == reviewer.id
    assert updated.reviewer_comment == "Camera glare issue."


def test_invalid_status_transition_is_rejected(db_session: Session, test_environment: dict):
    """13. Status transitions from VERIFIED or FALSE_POSITIVE back to PENDING are rejected."""
    session = test_environment["session"]
    admin = test_environment["admin"]

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="VERIFIED",
    )
    db_session.add(alert)
    db_session.commit()

    with pytest.raises(ValueError, match="cannot be modified"):
        AlertService.review_alert(db_session, alert.id, admin, "FALSE_POSITIVE", "Attempt change")


def test_false_positive_requires_reviewer_comment(db_session: Session, test_environment: dict):
    """14. FALSE_POSITIVE review requires a non-empty reviewer comment."""
    session = test_environment["session"]
    reviewer = test_environment["reviewer"]

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    with pytest.raises(ValueError, match="mandatory when marking an alert as FALSE_POSITIVE"):
        AlertService.review_alert(db_session, alert.id, reviewer, "FALSE_POSITIVE", "")

    with pytest.raises(ValueError, match="mandatory when marking an alert as FALSE_POSITIVE"):
        AlertService.review_alert(db_session, alert.id, reviewer, "FALSE_POSITIVE", None)


def test_reviewer_identity_derived_from_authenticated_user(
    client: TestClient, db_session: Session, test_environment: dict
):
    """15. Reviewer identity is derived securely from authentication token, not request body."""
    session = test_environment["session"]
    reviewer = test_environment["reviewer"]
    headers = make_headers(reviewer)

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    res = client.patch(
        f"/api/v1/alerts/{alert.id}/review",
        headers=headers,
        json={"status": "VERIFIED", "reviewer_comment": "Reviewed by token-authenticated user."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VERIFIED"
    assert data["reviewed_by"] == reviewer.id


# =========================================================================
# 3. Security, Authorization & API Tests
# =========================================================================

def test_unauthorized_users_cannot_review(client: TestClient, db_session: Session, test_environment: dict):
    """16. Centre staff users without ADMIN or REVIEWER roles cannot review alerts."""
    session = test_environment["session"]
    staff_a = test_environment["staff_a"]
    headers = make_headers(staff_a)

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    res = client.patch(
        f"/api/v1/alerts/{alert.id}/review",
        headers=headers,
        json={"status": "VERIFIED", "reviewer_comment": "Staff review attempt"},
    )
    assert res.status_code == 403


def test_unauthorized_users_cannot_access_evidence(client: TestClient, db_session: Session, test_environment: dict):
    """17. Non-admin users from other centres cannot access alerts/evidence for another centre."""
    session = test_environment["session"]
    staff_b = test_environment["staff_b"]  # Centre B staff
    headers = make_headers(staff_b)

    alert = Alert(
        centre_id=session.centre_id,  # Centre A alert
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    # Attempt to view detail of Centre A alert
    res = client.get(f"/api/v1/alerts/{alert.id}", headers=headers)
    assert res.status_code == 403


def test_alert_evidence_references_real_snapshots(db_session: Session, test_environment: dict):
    """18. Evidence records point to real database snapshots."""
    session = test_environment["session"]
    snap = test_environment["snapshots"][0]

    alert = Alert(
        centre_id=session.centre_id,
        monitoring_session_id=session.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        status="PENDING",
    )
    db_session.add(alert)
    db_session.flush()

    evidence = AlertEvidence(
        alert_id=alert.id,
        snapshot_id=snap.id,
        evidence_type="ATTENDANCE_SNAPSHOT",
    )
    db_session.add(evidence)
    db_session.commit()

    retrieved = db_session.query(AlertEvidence).filter(AlertEvidence.alert_id == alert.id).first()
    assert retrieved is not None
    assert retrieved.snapshot_id == snap.id
    assert retrieved.snapshot.file_path == "snap1.jpg"


def test_invalid_alert_id_returns_404(client: TestClient, test_environment: dict):
    """19. Requesting a non-existent alert returns 404."""
    admin = test_environment["admin"]
    headers = make_headers(admin)

    res = client.get("/api/v1/alerts/999999", headers=headers)
    assert res.status_code == 404

    res_review = client.patch(
        "/api/v1/alerts/999999/review",
        headers=headers,
        json={"status": "VERIFIED"},
    )
    assert res_review.status_code == 404 or res_review.status_code == 400


def test_centre_level_authorization_in_list(client: TestClient, db_session: Session, test_environment: dict):
    """20. Staff user only sees alerts belonging to their authorized centre."""
    centre_a = test_environment["centre_a"]
    centre_b = test_environment["centre_b"]
    staff_a = test_environment["staff_a"]

    alert_a = Alert(centre_id=centre_a.id, alert_type="ATTENDANCE_DISCREPANCY", status="PENDING")
    alert_b = Alert(centre_id=centre_b.id, alert_type="INFRASTRUCTURE_DISCREPANCY", status="PENDING")
    db_session.add_all([alert_a, alert_b])
    db_session.commit()

    headers_staff_a = make_headers(staff_a)
    res = client.get("/api/v1/alerts", headers=headers_staff_a)
    assert res.status_code == 200
    alerts = res.json()
    alert_ids = [a["id"] for a in alerts]
    assert alert_a.id in alert_ids
    assert alert_b.id not in alert_ids
