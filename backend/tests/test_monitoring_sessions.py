"""Tests for Monitoring Session management and Physical Attendance (Module 7)."""

import pytest
from datetime import date
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.core.security import get_password_hash, create_access_token


@pytest.fixture
def test_setup(db_session):
    """Sets up Admin, Reviewer, Centre Users, Centres, and Cameras."""
    # 1. Admin user
    admin = User(
        name="Admin User",
        email="admin_m7@sih.gov.in",
        password_hash=get_password_hash("AdminPass123!"),
        role="ADMIN",
    )
    db_session.add(admin)

    # 2. Reviewer user
    reviewer = User(
        name="Auditor Reviewer",
        email="reviewer_m7@sih.gov.in",
        password_hash=get_password_hash("ReviewerPass123!"),
        role="REVIEWER",
    )
    db_session.add(reviewer)

    # 3. Two Training Centres
    centre_a = Centre(
        centre_code="DELHI-001",
        name="Delhi Skill Centre",
        location="Connaught Place, Delhi",
        status="ACTIVE",
    )
    centre_b = Centre(
        centre_code="MUMBAI-002",
        name="Mumbai Vocational Hub",
        location="Andheri East, Mumbai",
        status="ACTIVE",
    )
    db_session.add_all([centre_a, centre_b])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(reviewer)
    db_session.refresh(centre_a)
    db_session.refresh(centre_b)

    # 4. Centre User assigned to Centre A
    centre_user_a = User(
        name="Centre A Operator",
        email="operator_a@sih.gov.in",
        password_hash=get_password_hash("OperatorPass123!"),
        role="CENTRE_USER",
        centre_id=centre_a.id,
    )
    db_session.add(centre_user_a)

    # 5. Cameras for each centre
    cam_a = Camera(
        centre_id=centre_a.id,
        name="Classroom 101 Front",
        source_type="RTSP",
        source_url="rtsp://192.168.1.101/live",
        is_active=True,
    )
    cam_b = Camera(
        centre_id=centre_b.id,
        name="Workshop B Main",
        source_type="VIDEO_FILE",
        source_url="/data/input/workshop_b.mp4",
        is_active=True,
    )
    db_session.add_all([centre_user_a, cam_a, cam_b])
    db_session.commit()
    db_session.refresh(centre_user_a)
    db_session.refresh(cam_a)
    db_session.refresh(cam_b)

    # Create tokens
    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    reviewer_token = create_access_token({"sub": str(reviewer.id), "email": reviewer.email, "role": "REVIEWER"})
    user_a_token = create_access_token({"sub": str(centre_user_a.id), "email": centre_user_a.email, "role": "CENTRE_USER"})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "reviewer_headers": {"Authorization": f"Bearer {reviewer_token}"},
        "user_a_headers": {"Authorization": f"Bearer {user_a_token}"},
        "centre_a": centre_a,
        "centre_b": centre_b,
        "cam_a": cam_a,
        "cam_b": cam_b,
    }


def test_create_valid_session(client, test_setup):
    """1. Create a valid monitoring session with anonymous physical attendance."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={
            "centre_id": c_a.id,
            "camera_id": cam_a.id,
            "physical_attendance": 28,
            "session_date": str(date.today()),
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["centre_id"] == c_a.id
    assert data["camera_id"] == cam_a.id
    assert data["physical_attendance"] == 28
    assert data["status"] == "PENDING"
    assert data["started_at"] is None
    assert data["ended_at"] is None
    assert data["centre"]["centre_code"] == "DELHI-001"
    assert data["camera"]["name"] == "Classroom 101 Front"


def test_reject_negative_physical_attendance(client, test_setup):
    """2. Reject negative physical attendance headcount."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={
            "centre_id": c_a.id,
            "camera_id": cam_a.id,
            "physical_attendance": -5,
        },
    )
    assert res.status_code in [400, 422]


def test_reject_invalid_centre(client, test_setup):
    """3. Reject creating session for a non-existent centre."""
    cam_a = test_setup["cam_a"]

    res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={
            "centre_id": 999999,
            "camera_id": cam_a.id,
            "physical_attendance": 15,
        },
    )
    assert res.status_code == 404
    assert "Centre with id 999999 not found" in res.json()["detail"]


def test_reject_invalid_camera(client, test_setup):
    """4. Reject creating session with non-existent camera."""
    c_a = test_setup["centre_a"]

    res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={
            "centre_id": c_a.id,
            "camera_id": 999999,
            "physical_attendance": 20,
        },
    )
    assert res.status_code == 404
    assert "Camera with id 999999 not found" in res.json()["detail"]


def test_reject_camera_belonging_to_another_centre(client, test_setup):
    """5. Reject creating session with camera belonging to a different centre."""
    c_a = test_setup["centre_a"]
    cam_b = test_setup["cam_b"]  # Belongs to centre_b

    res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={
            "centre_id": c_a.id,
            "camera_id": cam_b.id,
            "physical_attendance": 30,
        },
    )
    assert res.status_code == 400
    assert "belongs to centre" in res.json()["detail"]


def test_start_pending_session(client, test_setup):
    """6. Start a PENDING session -> Transitions to RUNNING with started_at timestamp."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    create_res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 25},
    )
    session_id = create_res.json()["id"]

    start_res = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/start",
        headers=test_setup["admin_headers"],
    )
    assert start_res.status_code == 200
    data = start_res.json()
    assert data["status"] == "RUNNING"
    assert data["started_at"] is not None
    assert data["ended_at"] is None


def test_reject_starting_running_session_again(client, test_setup):
    """7. Reject starting an already RUNNING session."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    create_res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 20},
    )
    session_id = create_res.json()["id"]

    # Start first time
    client.post(f"/api/v1/monitoring/sessions/{session_id}/start", headers=test_setup["admin_headers"])

    # Attempt to start second time
    retry_res = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/start",
        headers=test_setup["admin_headers"],
    )
    assert retry_res.status_code == 400
    assert "already RUNNING" in retry_res.json()["detail"]


def test_complete_running_session(client, test_setup):
    """8. Complete a RUNNING session -> Transitions to COMPLETED with ended_at timestamp."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    create_res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 32},
    )
    session_id = create_res.json()["id"]

    # Start session
    client.post(f"/api/v1/monitoring/sessions/{session_id}/start", headers=test_setup["admin_headers"])

    # Complete session
    comp_res = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/complete",
        headers=test_setup["admin_headers"],
    )
    assert comp_res.status_code == 200
    data = comp_res.json()
    assert data["status"] == "COMPLETED"
    assert data["started_at"] is not None
    assert data["ended_at"] is not None


def test_reject_completing_pending_session(client, test_setup):
    """9. Reject completing a session that is still in PENDING state."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    create_res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 18},
    )
    session_id = create_res.json()["id"]

    # Attempt completion without starting
    comp_res = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/complete",
        headers=test_setup["admin_headers"],
    )
    assert comp_res.status_code == 400
    assert "status 'PENDING'" in comp_res.json()["detail"]


def test_retrieve_session_list_and_filters(client, test_setup):
    """10. Retrieve session list with centre and status filters."""
    c_a = test_setup["centre_a"]
    c_b = test_setup["centre_b"]
    cam_a = test_setup["cam_a"]
    cam_b = test_setup["cam_b"]

    # Create session for centre A
    res_a = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 10},
    )
    s_a_id = res_a.json()["id"]
    client.post(f"/api/v1/monitoring/sessions/{s_a_id}/start", headers=test_setup["admin_headers"])

    # Create session for centre B
    client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_b.id, "camera_id": cam_b.id, "physical_attendance": 15},
    )

    # 10a. All sessions
    list_all = client.get("/api/v1/monitoring/sessions", headers=test_setup["admin_headers"])
    assert list_all.status_code == 200
    assert len(list_all.json()) >= 2

    # 10b. Filter by centre_id
    list_filtered = client.get(
        f"/api/v1/monitoring/sessions?centre_id={c_a.id}",
        headers=test_setup["admin_headers"],
    )
    assert list_filtered.status_code == 200
    assert all(s["centre_id"] == c_a.id for s in list_filtered.json())

    # 10c. Filter by status
    list_running = client.get(
        "/api/v1/monitoring/sessions?status=RUNNING",
        headers=test_setup["admin_headers"],
    )
    assert list_running.status_code == 200
    assert all(s["status"] == "RUNNING" for s in list_running.json())


def test_retrieve_session_details(client, test_setup):
    """11. Retrieve session details including centre and camera metadata."""
    c_a = test_setup["centre_a"]
    cam_a = test_setup["cam_a"]

    create_res = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["admin_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 44},
    )
    s_id = create_res.json()["id"]

    detail_res = client.get(
        f"/api/v1/monitoring/sessions/{s_id}",
        headers=test_setup["admin_headers"],
    )
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == s_id
    assert data["physical_attendance"] == 44
    assert data["centre"]["id"] == c_a.id
    assert data["centre"]["name"] == "Delhi Skill Centre"
    assert data["camera"]["id"] == cam_a.id
    assert data["camera"]["name"] == "Classroom 101 Front"


def test_authentication_and_authorization(client, test_setup):
    """12. Enforce authentication and role permissions."""
    c_a = test_setup["centre_a"]
    c_b = test_setup["centre_b"]
    cam_a = test_setup["cam_a"]
    cam_b = test_setup["cam_b"]

    # 12a. Unauthenticated access blocked
    unauth_res = client.post(
        "/api/v1/monitoring/sessions",
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 10},
    )
    assert unauth_res.status_code == 401

    # 12b. Reviewer cannot create sessions (Read-only role)
    rev_create = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["reviewer_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 10},
    )
    assert rev_create.status_code == 403

    # 12c. Reviewer can view sessions
    rev_list = client.get(
        "/api/v1/monitoring/sessions",
        headers=test_setup["reviewer_headers"],
    )
    assert rev_list.status_code == 200

    # 12d. Centre User can create session for their assigned Centre A
    cu_create = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["user_a_headers"],
        json={"centre_id": c_a.id, "camera_id": cam_a.id, "physical_attendance": 22},
    )
    assert cu_create.status_code == 201
    s_a_id = cu_create.json()["id"]

    # 12e. Centre User blocked from cross-centre creation (Centre B)
    cu_cross_create = client.post(
        "/api/v1/monitoring/sessions",
        headers=test_setup["user_a_headers"],
        json={"centre_id": c_b.id, "camera_id": cam_b.id, "physical_attendance": 22},
    )
    assert cu_cross_create.status_code == 403

    # 12f. Centre User can start their own centre's session
    cu_start = client.post(
        f"/api/v1/monitoring/sessions/{s_a_id}/start",
        headers=test_setup["user_a_headers"],
    )
    assert cu_start.status_code == 200
    assert cu_start.json()["status"] == "RUNNING"
