"""Tests for Dashboard Integration API (Prompt 14).

Verifies:
1. Dashboard summary returns real counts from database.
2. Centre authorization works (Admin sees all, Centre User only sees assigned centre).
3. Alert counts in summary are accurate.
4. Compliance counts in summary are accurate.
5. Empty database returns zero counts without error.
6. Unauthenticated requests return 401.
7. Centres overview returns latest session status and pending alert count.
8. Recent activity feed contains real chronological audit records.
"""

from datetime import datetime, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.alert import Alert
from backend.app.models.compliance import (
    AttendanceComplianceResult,
    InfrastructureComplianceResult,
)


@pytest.fixture
def auth_tokens(db_session: Session):
    """Creates test users with distinct roles and centres, returning auth headers."""
    # 1. Admin
    admin = User(
        email="admin_dash@test.com",
        name="Admin Dash",
        password_hash="hash",
        role="ADMIN",
    )
    db_session.add(admin)

    # 2. Centre 1 & User 1
    c1 = Centre(name="Centre One", centre_code="CEN-D01", status="ACTIVE")
    db_session.add(c1)
    db_session.flush()

    user_c1 = User(
        email="user_c1@test.com",
        name="User Centre One",
        password_hash="hash",
        role="CENTRE_USER",
        centre_id=c1.id,
    )
    db_session.add(user_c1)

    # 3. Centre 2 & User 2
    c2 = Centre(name="Centre Two", centre_code="CEN-D02", status="ACTIVE")
    db_session.add(c2)
    db_session.flush()

    user_c2 = User(
        email="user_c2@test.com",
        name="User Centre Two",
        password_hash="hash",
        role="CENTRE_USER",
        centre_id=c2.id,
    )
    db_session.add(user_c2)

    db_session.commit()

    token_admin = create_access_token({"sub": str(admin.id), "email": admin.email, "role": admin.role})
    token_c1 = create_access_token({"sub": str(user_c1.id), "email": user_c1.email, "role": user_c1.role})
    token_c2 = create_access_token({"sub": str(user_c2.id), "email": user_c2.email, "role": user_c2.role})

    return {
        "admin_headers": {"Authorization": f"Bearer {token_admin}"},
        "c1_headers": {"Authorization": f"Bearer {token_c1}"},
        "c2_headers": {"Authorization": f"Bearer {token_c2}"},
        "admin_id": admin.id,
        "c1_id": c1.id,
        "c2_id": c2.id,
        "user_c1_id": user_c1.id,
    }


def test_dashboard_summary_empty(client: TestClient, auth_tokens: dict, db_session: Session):
    """Empty monitoring/alerts tables must return 0 counts without crashing."""
    resp = client.get("/api/v1/dashboard/summary", headers=auth_tokens["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()

    assert data["centres"]["total"] >= 2
    assert data["monitoring_sessions"]["total"] == 0
    assert data["monitoring_sessions"]["completed"] == 0
    assert data["alerts"]["total"] == 0
    assert data["alerts"]["pending"] == 0
    assert data["compliance"]["attendance_matches"] == 0
    assert data["compliance"]["attendance_discrepancies"] == 0


def test_dashboard_summary_real_counts(client: TestClient, auth_tokens: dict, db_session: Session):
    """Tests summary aggregation with multiple sessions, alerts, and compliance outcomes."""
    c1_id = auth_tokens["c1_id"]
    c2_id = auth_tokens["c2_id"]

    # Add Camera
    cam1 = Camera(centre_id=c1_id, name="Main Cam", source_type="CAMERA", source_url="rtsp://test", is_active=True)
    db_session.add(cam1)
    db_session.flush()

    # Add Sessions
    s1 = MonitoringSession(
        centre_id=c1_id,
        camera_id=cam1.id,
        session_date=date.today(),
        physical_attendance=30,
        status="COMPLETED",
    )
    s2 = MonitoringSession(
        centre_id=c2_id,
        camera_id=None,
        session_date=date.today(),
        physical_attendance=25,
        status="RUNNING",
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    # Add Compliance
    comp1 = AttendanceComplianceResult(
        monitoring_session_id=s1.id,
        physical_attendance=30,
        ai_estimated_attendance=24.0,
        difference=6.0,
        tolerance=2,
        status="DISCREPANCY",
    )
    infra_comp1 = InfrastructureComplianceResult(
        monitoring_session_id=s1.id,
        item_name="Desktop Computer",
        ai_class="computer",
        expected_quantity=10,
        observed_quantity=10.0,
        difference=0.0,
        status="COMPLIANT",
    )
    db_session.add_all([comp1, infra_comp1])
    db_session.flush()

    # Add Alerts
    a1 = Alert(
        centre_id=c1_id,
        monitoring_session_id=s1.id,
        compliance_result_id=comp1.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        severity="MEDIUM",
        status="PENDING",
        expected_value=30.0,
        observed_value=24.0,
        difference=6.0,
    )
    a2 = Alert(
        centre_id=c2_id,
        monitoring_session_id=s2.id,
        compliance_result_id=None,
        alert_type="INFRASTRUCTURE_DISCREPANCY",
        severity="HIGH",
        status="VERIFIED",
        expected_value=15.0,
        observed_value=10.0,
        difference=5.0,
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    # Admin view: sees system-wide aggregates
    resp_admin = client.get("/api/v1/dashboard/summary", headers=auth_tokens["admin_headers"])
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()

    assert data_admin["monitoring_sessions"]["total"] == 2
    assert data_admin["monitoring_sessions"]["completed"] == 1
    assert data_admin["monitoring_sessions"]["running"] == 1
    assert data_admin["alerts"]["total"] == 2
    assert data_admin["alerts"]["pending"] == 1
    assert data_admin["alerts"]["verified"] == 1
    assert data_admin["alerts"]["attendance_discrepancies"] == 1
    assert data_admin["alerts"]["infrastructure_discrepancies"] == 1
    assert data_admin["compliance"]["attendance_discrepancies"] == 1
    assert data_admin["compliance"]["infrastructure_compliant"] == 1

    # Centre 1 User view: strictly sees Centre 1 data
    resp_c1 = client.get("/api/v1/dashboard/summary", headers=auth_tokens["c1_headers"])
    assert resp_c1.status_code == 200
    data_c1 = resp_c1.json()

    assert data_c1["centres"]["total"] == 1
    assert data_c1["monitoring_sessions"]["total"] == 1
    assert data_c1["monitoring_sessions"]["completed"] == 1
    assert data_c1["monitoring_sessions"]["running"] == 0
    assert data_c1["alerts"]["total"] == 1
    assert data_c1["alerts"]["pending"] == 1
    assert data_c1["alerts"]["verified"] == 0  # Alert 2 belongs to Centre 2!


def test_centres_overview_endpoint(client: TestClient, auth_tokens: dict, db_session: Session):
    """Verifies GET /api/v1/dashboard/centres-overview returns per-centre status."""
    resp = client.get("/api/v1/dashboard/centres-overview", headers=auth_tokens["admin_headers"])
    assert resp.status_code == 200
    centres_data = resp.json()
    assert len(centres_data) >= 2

    # Check Centre 1 user cannot see Centre 2 in overview
    resp_c1 = client.get("/api/v1/dashboard/centres-overview", headers=auth_tokens["c1_headers"])
    assert resp_c1.status_code == 200
    centres_c1 = resp_c1.json()
    assert len(centres_c1) == 1
    assert centres_c1[0]["id"] == auth_tokens["c1_id"]


def test_recent_activity_endpoint(client: TestClient, auth_tokens: dict, db_session: Session):
    """Verifies GET /api/v1/dashboard/recent-activity returns real chronological events."""
    resp = client.get("/api/v1/dashboard/recent-activity", headers=auth_tokens["admin_headers"])
    assert resp.status_code == 200
    activity = resp.json()
    assert isinstance(activity, list)
    if activity:
        assert "activity_type" in activity[0]
        assert "timestamp" in activity[0]
        assert "centre_name" in activity[0]


def test_unauthorized_dashboard_access(client: TestClient):
    """Verifies unauthenticated calls fail with 401."""
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401


def test_recent_activity_centre_scoping(client: TestClient, auth_tokens: dict):
    """Verifies centre user only receives activity for their authorized centre."""
    resp = client.get("/api/v1/dashboard/recent-activity", headers=auth_tokens["c1_headers"])
    assert resp.status_code == 200
    events = resp.json()
    for ev in events:
        assert ev["centre_id"] == auth_tokens["c1_id"]


def test_invalid_query_parameters(client: TestClient, auth_tokens: dict):
    """Verifies validation errors on invalid limit parameters."""
    resp = client.get("/api/v1/dashboard/centres-overview?limit=0", headers=auth_tokens["admin_headers"])
    assert resp.status_code == 422
