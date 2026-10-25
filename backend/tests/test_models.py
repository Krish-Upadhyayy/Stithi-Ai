"""Database models creation and relationship integrity tests."""

from datetime import datetime
from backend.app.models import (
    Centre,
    User,
    Camera,
    MonitoringSession,
    Snapshot,
    AttendanceObservation,
    InventoryItem,
    InfrastructureObservation,
    Alert,
)
from backend.app.core.security import get_password_hash, verify_password


def test_models_creation_and_relationships(db_session):
    # 1. Centre
    centre = Centre(
        centre_code="TC-101",
        name="Skill Training Institute Bangalore",
        location="Electronic City, Bangalore",
        status="ACTIVE"
    )
    db_session.add(centre)
    db_session.commit()
    assert centre.id is not None
    assert centre.centre_code == "TC-101"

    # 2. User
    pw_hash = get_password_hash("SecretPassword123")
    assert verify_password("SecretPassword123", pw_hash)
    user = User(
        name="Admin Inspector",
        email="inspector@sih.gov.in",
        password_hash=pw_hash,
        role="ADMIN",
        centre_id=centre.id
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.centre.centre_code == "TC-101"

    # 3. Camera
    camera = Camera(
        centre_id=centre.id,
        name="Classroom 1 Front View",
        source_type="VIDEO_FILE",
        source_url="data/input/classroom_sample.mp4",
        is_active=True
    )
    db_session.add(camera)
    db_session.commit()
    assert camera.id is not None

    # 4. Monitoring Session (Physical attendance is integer count only, anonymous)
    session = MonitoringSession(
        centre_id=centre.id,
        camera_id=camera.id,
        physical_attendance=35,
        started_at=datetime.utcnow(),
        status="RUNNING"
    )
    db_session.add(session)
    db_session.commit()
    assert session.id is not None
    assert session.physical_attendance == 35

    # 5. Snapshot
    snapshot = Snapshot(
        monitoring_session_id=session.id,
        file_path="data/snapshots/TC101_seq_001.jpg",
        sequence_number=1,
        processing_status="PROCESSED"
    )
    db_session.add(snapshot)
    db_session.commit()
    assert snapshot.id is not None

    # 6. Attendance Observation (Anonymous count)
    att_obs = AttendanceObservation(
        snapshot_id=snapshot.id,
        observed_count=28,
        confidence_score=0.92,
        model_version="YOLO26-Presence-Baseline"
    )
    db_session.add(att_obs)
    db_session.commit()
    assert att_obs.id is not None
    assert att_obs.observed_count == 28

    # 7. Inventory Item (Sanctioned Excel item)
    inventory = InventoryItem(
        centre_id=centre.id,
        item_name="Computer",
        category="IT Lab",
        expected_quantity=40
    )
    db_session.add(inventory)
    db_session.commit()
    assert inventory.id is not None

    # 8. Infrastructure Observation (Asset count)
    infra_obs = InfrastructureObservation(
        snapshot_id=snapshot.id,
        inventory_item_id=inventory.id,
        asset_type="Computer",
        detected_quantity=32,
        confidence=0.88
    )
    db_session.add(infra_obs)
    db_session.commit()
    assert infra_obs.id is not None
    assert infra_obs.detected_quantity == 32

    # 9. Alert
    alert = Alert(
        centre_id=centre.id,
        session_id=session.id,
        snapshot_id=snapshot.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        severity="HIGH",
        expected_value=35,
        observed_value=28,
        difference=7,
        description="Physical headcount (35) exceeds AI observed count (28) by 7.",
        status="PENDING"
    )
    db_session.add(alert)
    db_session.commit()
    assert alert.id is not None
    assert alert.difference == 7
    assert alert.status == "PENDING"
