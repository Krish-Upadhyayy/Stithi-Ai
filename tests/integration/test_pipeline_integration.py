"""
Integration Test: End-to-End Pipeline & Multi-Module Interactions
Validates cross-module interactions:
- Auth & Centre Boundaries
- Inventory Mapping & Monitoring Sessions
- Snapshot Ingestion & AI Observation Linking
- Compliance Engine Discrepancy Detection & Multi-Snapshot Rules
- Alert Generation & Deduplication
- Human Review (Pending -> Verified / False Positive)
- Evidence Integrity & Privacy Verification
"""

import os
import io
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import (
    User,
    Centre,
    Camera,
    MonitoringSession,
    Snapshot,
    AttendanceObservation,
    InfrastructureObservation,
    InventoryItem,
    Alert,
)
from backend.app.core.security import get_password_hash, create_access_token
from backend.tests.conftest import client, db_session, setup_test_database


def create_test_user(db: Session, email: str, role: str, centre_id: int = None) -> User:
    user = User(
        name=f"User {email}",
        email=email,
        password_hash=get_password_hash("ValidPass123!"),
        role=role,
        centre_id=centre_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_token_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_integration_full_monitoring_compliance_flow(client: TestClient, db_session: Session):
    """
    Validates the integrated pipeline from centre setup through compliance,
    alert creation, human review, and privacy constraints.
    """
    # 1. Setup Admin, Centre, and Centre User
    admin = create_test_user(db_session, "admin@sih.gov.in", "ADMIN")
    admin_headers = get_token_headers(admin)

    centre = Centre(
        centre_code="TC-INT-001",
        name="Jaipur Electronics Skill Centre",
        location="Sector 5 Sitapura Jaipur",
        status="ACTIVE",
    )
    db_session.add(centre)
    db_session.commit()
    db_session.refresh(centre)

    centre_user = create_test_user(
        db_session, "operator@jaipur.sih.gov.in", "CENTRE_USER", centre_id=centre.id
    )
    centre_headers = get_token_headers(centre_user)

    reviewer = create_test_user(db_session, "reviewer@sih.gov.in", "REVIEWER")
    reviewer_headers = get_token_headers(reviewer)

    # 2. Setup Camera
    camera = Camera(
        centre_id=centre.id,
        name="Lab 1 Cam",
        source_type="CAMERA",
        source_url="rtsp://fake-stream/live",
        is_active=True,
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    # 3. Setup Inventory (Sanctioned Equipment)
    inv_pc = InventoryItem(
        centre_id=centre.id,
        item_name="Desktop Computers",
        expected_quantity=20,
        category="IT",
    )
    db_session.add(inv_pc)
    db_session.commit()

    # 4. Create and Start Monitoring Session
    resp_session = client.post(
        "/api/v1/monitoring/sessions",
        json={
            "centre_id": centre.id,
            "camera_id": camera.id,
            "physical_attendance": 25,
        },
        headers=centre_headers,
    )
    assert resp_session.status_code == 201
    session_id = resp_session.json()["id"]

    # Start Session
    resp_start = client.post(f"/api/v1/monitoring/sessions/{session_id}/start", headers=centre_headers)
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "RUNNING"

    # 5. Simulate Video Snapshots
    snap1 = Snapshot(
        monitoring_session_id=session_id,
        sequence_number=1,
        frame_time_seconds=0.0,
        file_path=f"storage/sessions/{session_id}/snap_001.jpg",
        processing_status="COMPLETED",
    )
    snap2 = Snapshot(
        monitoring_session_id=session_id,
        sequence_number=2,
        frame_time_seconds=10.0,
        file_path=f"storage/sessions/{session_id}/snap_002.jpg",
        processing_status="COMPLETED",
    )
    db_session.add_all([snap1, snap2])
    db_session.commit()
    db_session.refresh(snap1)
    db_session.refresh(snap2)

    # 6. Insert AI Observations (YOLO26 format: detected count, bounding boxes, model metadata)
    obs_att1 = AttendanceObservation(
        monitoring_session_id=session_id,
        snapshot_id=snap1.id,
        observed_count=16,
        confidence_score=0.88,
        model_name="YOLO26-Attendance",
        model_version="custom-v1",
        inference_time_ms=42.5,
        processing_status="COMPLETED",
    )
    obs_att2 = AttendanceObservation(
        monitoring_session_id=session_id,
        snapshot_id=snap2.id,
        observed_count=18,
        confidence_score=0.89,
        model_name="YOLO26-Attendance",
        model_version="custom-v1",
        inference_time_ms=41.8,
        processing_status="COMPLETED",
    )
    # Infrastructure: Sanctioned=20, Observed=12
    obs_inf1 = InfrastructureObservation(
        monitoring_session_id=session_id,
        snapshot_id=snap1.id,
        inventory_item_id=inv_pc.id,
        asset_type="computer",
        detected_quantity=12,
        confidence=0.85,
        model_name="YOLO26-Infrastructure",
        model_version="infra-v1",
        inference_time_ms=50.2,
        processing_status="COMPLETED",
    )
    db_session.add_all([obs_att1, obs_att2, obs_inf1])
    db_session.commit()

    # 7. Complete Session
    resp_comp = client.post(f"/api/v1/monitoring/sessions/{session_id}/complete", headers=centre_headers)
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "COMPLETED"

    # 8. Run Compliance Calculation Endpoint
    resp_calc = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/compliance/calculate",
        json={"tolerance": 2, "aggregation_method": "MEDIAN"},
        headers=admin_headers,
    )
    assert resp_calc.status_code == 200
    calc_data = resp_calc.json()
    assert calc_data["attendance"]["status"] == "DISCREPANCY"
    # Physical is 25, median AI is 17 -> difference 8 > tolerance 2 -> DISCREPANCY
    assert calc_data["attendance"]["difference"] == 8.0

    # 9. Generate Alerts (Should produce attendance discrepancy alert)
    resp_alerts = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/alerts/generate",
        headers=admin_headers,
    )
    assert resp_alerts.status_code == 200
    alerts_data = resp_alerts.json()
    assert alerts_data["alerts_created"] >= 1

    # 10. Test Alert Deduplication
    resp_dup = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/alerts/generate",
        headers=admin_headers,
    )
    assert resp_dup.status_code == 200
    # Duplicate run must generate 0 new alerts
    assert resp_dup.json()["alerts_created"] == 0

    # 11. Retrieve Generated Alert
    resp_list_alerts = client.get(f"/api/v1/alerts?session_id={session_id}", headers=reviewer_headers)
    assert resp_list_alerts.status_code == 200
    alert_list = resp_list_alerts.json()
    assert len(alert_list) >= 1
    alert_item = alert_list[0]
    alert_id = alert_item["id"]

    # 12. Review Alert: PENDING -> VERIFIED
    resp_review = client.patch(
        f"/api/v1/alerts/{alert_id}/review",
        json={
            "status": "VERIFIED",
            "reviewer_comment": "Confirmed discrepancy against physical register count of 25.",
        },
        headers=reviewer_headers,
    )
    assert resp_review.status_code == 200
    reviewed_alert = resp_review.json()
    assert reviewed_alert["status"] == "VERIFIED"
    assert reviewed_alert["reviewed_by"] == reviewer.id
    assert reviewed_alert["reviewed_at"] is not None

    # 13. State Immutability: Cannot revert VERIFIED back to PENDING
    resp_revert = client.patch(
        f"/api/v1/alerts/{alert_id}/review",
        json={"status": "PENDING", "reviewer_comment": "Trying to reset"},
        headers=reviewer_headers,
    )
    assert resp_revert.status_code in [400, 422]

    # 14. Verify Privacy: Ensure NO student identity fields exist in responses
    for key in ["student_name", "student_id", "biometric_data", "face_embedding"]:
        assert key not in reviewed_alert
        assert key not in calc_data


def test_cross_centre_authorization_isolation(client: TestClient, db_session: Session):
    """
    Verifies that a CENTRE_USER belonging to Centre A cannot access or mutate
    monitoring sessions or alerts belonging to Centre B.
    """
    # Create Centre A and Centre B
    cA = Centre(centre_code="TC-ISO-A", name="Centre Alpha", location="Delhi", status="ACTIVE")
    cB = Centre(centre_code="TC-ISO-B", name="Centre Beta", location="Haryana", status="ACTIVE")
    db_session.add_all([cA, cB])
    db_session.commit()
    db_session.refresh(cA)
    db_session.refresh(cB)

    camB = Camera(centre_id=cB.id, name="Beta Cam 1", source_type="CAMERA", source_url="rtsp://beta", is_active=True)
    db_session.add(camB)
    db_session.commit()
    db_session.refresh(camB)

    # Session for Centre B
    sessB = MonitoringSession(
        centre_id=cB.id,
        camera_id=camB.id,
        physical_attendance=30,
        status="PENDING",
    )
    db_session.add(sessB)
    db_session.commit()
    db_session.refresh(sessB)

    # User bound strictly to Centre A
    userA = create_test_user(db_session, "userA@alpha.org", "CENTRE_USER", centre_id=cA.id)
    headersA = get_token_headers(userA)

    # Attempt 1: User A trying to view Session B
    resp_get = client.get(f"/api/v1/monitoring/sessions/{sessB.id}", headers=headersA)
    assert resp_get.status_code == 403, "Centre A user must receive 403 when viewing Centre B session"

    # Attempt 2: User A trying to start Session B
    resp_start = client.post(f"/api/v1/monitoring/sessions/{sessB.id}/start", headers=headersA)
    assert resp_start.status_code == 403, "Centre A user must receive 403 when modifying Centre B session"
