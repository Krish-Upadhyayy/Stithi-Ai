"""API routes and validation tests."""

import pytest
from backend.app.models.user import User
from backend.app.core.security import get_password_hash, create_access_token


@pytest.fixture
def admin_auth_header(db_session):
    admin = User(
        name="Route Test Admin",
        email="route_admin@sih.gov.in",
        password_hash=get_password_hash("RoutePass123!"),
        role="ADMIN",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}


def test_centre_routes(client, admin_auth_header):
    # 1. Create centre
    create_res = client.post(
        "/api/v1/centres",
        headers=admin_auth_header,
        json={
            "centre_code": "CENTRE-001",
            "name": "Delhi Skill Hub",
            "location": "Connaught Place, New Delhi",
            "status": "ACTIVE",
        },
    )
    assert create_res.status_code == 201
    centre_data = create_res.json()
    assert centre_data["centre_code"] == "CENTRE-001"
    centre_id = centre_data["id"]

    # 2. Get centre list
    list_res = client.get("/api/v1/centres", headers=admin_auth_header)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Get single centre
    get_res = client.get(f"/api/v1/centres/{centre_id}", headers=admin_auth_header)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Delhi Skill Hub"

    # 4. Duplicate centre error
    dup_res = client.post(
        "/api/v1/centres",
        headers=admin_auth_header,
        json={
            "centre_code": "CENTRE-001",
            "name": "Another Centre",
            "status": "ACTIVE",
        },
    )
    assert dup_res.status_code in [400, 409]

    # 5. Non-existent centre 404
    nf_res = client.get("/api/v1/centres/999999", headers=admin_auth_header)
    assert nf_res.status_code == 404


def test_session_routes(client, admin_auth_header):
    # Setup centre
    c_res = client.post(
        "/api/v1/centres",
        headers=admin_auth_header,
        json={
            "centre_code": "SESSION-C1",
            "name": "Mumbai Vocational Institute",
        },
    )
    c_id = c_res.json()["id"]

    # Create session with anonymous physical attendance
    s_res = client.post(
        "/api/v1/sessions",
        json={
            "centre_id": c_id,
            "physical_attendance": 42,
        },
    )
    assert s_res.status_code == 201
    assert s_res.json()["physical_attendance"] == 42
    assert s_res.json()["status"] == "PENDING"

    # Validation: negative attendance must fail with 422
    invalid_res = client.post(
        "/api/v1/sessions",
        json={
            "centre_id": c_id,
            "physical_attendance": -5,
        },
    )
    assert invalid_res.status_code == 422
    assert "ValidationError" in invalid_res.json()["error"]


def test_alert_routes(client, db_session):
    from backend.app.models import Centre, Alert

    centre = Centre(centre_code="ALERT-C1", name="Pune IT Training")
    db_session.add(centre)
    db_session.commit()

    alert = Alert(
        centre_id=centre.id,
        alert_type="ATTENDANCE_DISCREPANCY",
        severity="HIGH",
        expected_value=50,
        observed_value=30,
        difference=20,
        status="PENDING",
    )
    db_session.add(alert)
    db_session.commit()

    # List alerts
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Update status to VERIFIED
    patch_res = client.patch(f"/api/v1/alerts/{alert.id}/status", json={"status": "VERIFIED"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "VERIFIED"

    # Invalid status rejection
    inv_patch = client.patch(f"/api/v1/alerts/{alert.id}/status", json={"status": "INVALID_STATUS"})
    assert inv_patch.status_code == 400
