"""Centre and Camera management test suite covering all 12 required scenarios."""

import pytest
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.core.security import get_password_hash, create_access_token


@pytest.fixture
def auth_tokens(db_session):
    """Creates test admin and centre users, returning valid bearer auth headers."""
    admin = User(
        name="Administrator",
        email="admin_test@sih.gov.in",
        password_hash=get_password_hash("AdminPass123!"),
        role="ADMIN",
    )
    centre_user = User(
        name="Centre Operator",
        email="operator_test@sih.gov.in",
        password_hash=get_password_hash("OpPass123!"),
        role="CENTRE_USER",
    )
    db_session.add_all([admin, centre_user])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(centre_user)

    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    user_token = create_access_token({"sub": str(centre_user.id), "email": centre_user.email, "role": "CENTRE_USER"})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "user_headers": {"Authorization": f"Bearer {user_token}"},
        "admin": admin,
        "centre_user": centre_user,
    }


# 1. Create centre
def test_create_centre(client, auth_tokens):
    res = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={
            "centre_code": "TC-PUN-001",
            "name": "Pune Skill Development Centre",
            "location": "Shivaji Nagar, Pune, Maharashtra",
            "status": "ACTIVE",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["centre_code"] == "TC-PUN-001"
    assert data["name"] == "Pune Skill Development Centre"
    assert data["status"] == "ACTIVE"
    assert "id" in data
    assert data["camera_count"] == 0


# 2. Duplicate centre code
def test_duplicate_centre_code(client, auth_tokens):
    client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={
            "centre_code": "TC-DUP-001",
            "name": "First Centre",
            "location": "Location A",
            "status": "ACTIVE",
        },
    )
    dup_res = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={
            "centre_code": "TC-DUP-001",
            "name": "Second Centre with same code",
            "location": "Location B",
            "status": "ACTIVE",
        },
    )
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]


# 3. Get centres
def test_get_centres(client, auth_tokens):
    client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-LIST-01", "name": "List Centre 1", "status": "ACTIVE"},
    )
    client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-LIST-02", "name": "List Centre 2", "status": "ACTIVE"},
    )
    res = client.get("/api/v1/centres", headers=auth_tokens["admin_headers"])
    assert res.status_code == 200
    centres = res.json()
    assert len(centres) >= 2


# 4. Get centre by ID
def test_get_centre_by_id(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-GET-01", "name": "Target Centre", "status": "ACTIVE"},
    ).json()

    res = client.get(f"/api/v1/centres/{c['id']}", headers=auth_tokens["admin_headers"])
    assert res.status_code == 200
    assert res.json()["centre_code"] == "TC-GET-01"

    # Non-existent centre
    nf_res = client.get("/api/v1/centres/99999", headers=auth_tokens["admin_headers"])
    assert nf_res.status_code == 404


# 5. Update centre
def test_update_centre(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-UPD-01", "name": "Old Centre Name", "location": "Old Loc"},
    ).json()

    res = client.put(
        f"/api/v1/centres/{c['id']}",
        headers=auth_tokens["admin_headers"],
        json={"name": "Updated Centre Name", "location": "New Location Sector 5"},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["name"] == "Updated Centre Name"
    assert updated["location"] == "New Location Sector 5"
    assert updated["centre_code"] == "TC-UPD-01"


# 6. Activate/deactivate centre
def test_activate_deactivate_centre(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-STAT-01", "name": "Status Test Centre", "status": "ACTIVE"},
    ).json()

    # Deactivate via PATCH status
    patch_res = client.patch(
        f"/api/v1/centres/{c['id']}/status",
        headers=auth_tokens["admin_headers"],
        json={"status": "INACTIVE"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "INACTIVE"

    # Reactivate
    reactivate_res = client.patch(
        f"/api/v1/centres/{c['id']}/status",
        headers=auth_tokens["admin_headers"],
        json={"status": "ACTIVE"},
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["status"] == "ACTIVE"

    # Soft delete via DELETE
    del_res = client.delete(f"/api/v1/centres/{c['id']}", headers=auth_tokens["admin_headers"])
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "INACTIVE"


# 7. Create camera
def test_create_camera(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-CAM-01", "name": "Camera Testing Centre"},
    ).json()

    cam_res = client.post(
        f"/api/v1/centres/{c['id']}/cameras",
        headers=auth_tokens["admin_headers"],
        json={
            "name": "Classroom 101 Front",
            "source_type": "VIDEO_FILE",
            "source_url": "data/videos/classroom_test.mp4",
            "is_active": True,
        },
    )
    assert cam_res.status_code == 201
    cam = cam_res.json()
    assert cam["name"] == "Classroom 101 Front"
    assert cam["source_type"] == "VIDEO_FILE"
    assert cam["source_url"] == "data/videos/classroom_test.mp4"
    assert cam["centre_id"] == c["id"]
    assert cam["is_active"] is True


# 8. Get cameras for centre
def test_get_cameras_for_centre(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-CAM-LIST", "name": "Multi-Cam Centre"},
    ).json()

    client.post(
        f"/api/v1/centres/{c['id']}/cameras",
        headers=auth_tokens["admin_headers"],
        json={"name": "Cam 1", "source_type": "VIDEO_FILE", "source_url": "path1.mp4"},
    )
    client.post(
        f"/api/v1/centres/{c['id']}/cameras",
        headers=auth_tokens["admin_headers"],
        json={"name": "Cam 2", "source_type": "CAMERA", "source_url": "rtsp://192.168.1.10/stream1"},
    )

    res = client.get(f"/api/v1/centres/{c['id']}/cameras", headers=auth_tokens["admin_headers"])
    assert res.status_code == 200
    cameras = res.json()
    assert len(cameras) == 2

    # Check that centre response reports camera_count == 2
    c_check = client.get(f"/api/v1/centres/{c['id']}", headers=auth_tokens["admin_headers"]).json()
    assert c_check["camera_count"] == 2


# 9. Update camera
def test_update_camera(client, auth_tokens):
    c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-CAM-UPD", "name": "Camera Update Centre"},
    ).json()

    cam = client.post(
        f"/api/v1/centres/{c['id']}/cameras",
        headers=auth_tokens["admin_headers"],
        json={"name": "Old Camera Name", "source_type": "VIDEO_FILE", "source_url": "old.mp4"},
    ).json()

    # Update camera configuration
    upd_res = client.put(
        f"/api/v1/centres/{c['id']}/cameras/{cam['id']}",
        headers=auth_tokens["admin_headers"],
        json={"name": "Updated Lab Camera", "source_type": "CAMERA", "source_url": "rtsp://stream.local"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == "Updated Lab Camera"
    assert upd_res.json()["source_type"] == "CAMERA"

    # Status toggle
    status_res = client.patch(
        f"/api/v1/centres/{c['id']}/cameras/{cam['id']}/status",
        headers=auth_tokens["admin_headers"],
        json={"is_active": False},
    )
    assert status_res.status_code == 200
    assert status_res.json()["is_active"] is False


# 10. Camera belonging to another centre cannot be accessed incorrectly
def test_camera_cross_centre_isolation(client, auth_tokens):
    c1 = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-ISO-01", "name": "Centre Alpha"},
    ).json()
    c2 = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-ISO-02", "name": "Centre Beta"},
    ).json()

    # Add camera to c1
    cam1 = client.post(
        f"/api/v1/centres/{c1['id']}/cameras",
        headers=auth_tokens["admin_headers"],
        json={"name": "Alpha Cam", "source_type": "VIDEO_FILE", "source_url": "alpha.mp4"},
    ).json()

    # Attempt to access c1's camera using c2's URL path
    cross_get = client.get(
        f"/api/v1/centres/{c2['id']}/cameras/{cam1['id']}",
        headers=auth_tokens["admin_headers"],
    )
    assert cross_get.status_code == 404
    assert f"not found in centre {c2['id']}" in cross_get.json()["detail"]

    # Attempt to update c1's camera through c2's path
    cross_put = client.put(
        f"/api/v1/centres/{c2['id']}/cameras/{cam1['id']}",
        headers=auth_tokens["admin_headers"],
        json={"name": "Hijacked Camera"},
    )
    assert cross_put.status_code == 404


# 11. Unauthorized user cannot perform admin-only actions
def test_unauthorized_user_forbidden_admin_actions(client, auth_tokens):
    # Non-admin user attempts to create centre
    create_res = client.post(
        "/api/v1/centres",
        headers=auth_tokens["user_headers"],
        json={"centre_code": "TC-FORBIDDEN", "name": "Unauthorized Centre"},
    )
    assert create_res.status_code == 403
    assert "lacks required permission" in create_res.json()["detail"]

    # Non-admin user attempts to add camera to an existing centre
    admin_c = client.post(
        "/api/v1/centres",
        headers=auth_tokens["admin_headers"],
        json={"centre_code": "TC-FORBIDDEN-CAM", "name": "Admin Centre"},
    ).json()

    cam_res = client.post(
        f"/api/v1/centres/{admin_c['id']}/cameras",
        headers=auth_tokens["user_headers"],
        json={"name": "Unauthorized Cam", "source_type": "VIDEO_FILE", "source_url": "test.mp4"},
    )
    assert cam_res.status_code == 403


# 12. Unauthenticated request is rejected
def test_unauthenticated_requests_rejected(client):
    # GET centres without token
    res_get = client.get("/api/v1/centres")
    assert res_get.status_code == 401

    # POST centre without token
    res_post = client.post(
        "/api/v1/centres",
        json={"centre_code": "TC-NOAUTH", "name": "No Auth Centre"},
    )
    assert res_post.status_code == 401

    # GET cameras without token
    res_cams = client.get("/api/v1/centres/1/cameras")
    assert res_cams.status_code == 401
