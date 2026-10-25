"""Tests for Video & Snapshot Engine (Module 8)."""

import os
import tempfile
import pytest
import cv2
import numpy as np
from datetime import date
from io import BytesIO

from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.core.security import get_password_hash, create_access_token


def generate_test_mp4(num_frames: int = 30, fps: float = 10.0, width: int = 64, height: int = 64) -> bytes:
    """Dynamically generates a tiny valid in-memory MP4 video using OpenCV."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(num_frames):
            # Create a simple frame with color variation
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (i * 8 % 255, 120, 200)
            out.write(frame)
        out.release()

        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture
def m8_test_setup(db_session):
    """Sets up Admin, Reviewer, Centre User, Centre, Camera, and a test Session."""
    admin = User(
        name="Admin M8",
        email="admin_m8@sih.gov.in",
        password_hash=get_password_hash("AdminPass123!"),
        role="ADMIN",
    )
    reviewer = User(
        name="Reviewer M8",
        email="reviewer_m8@sih.gov.in",
        password_hash=get_password_hash("ReviewerPass123!"),
        role="REVIEWER",
    )
    centre = Centre(
        centre_code="C-M8-01",
        name="Jaipur Skilling Centre",
        location="Jaipur, Rajasthan",
        status="ACTIVE",
    )
    db_session.add_all([admin, reviewer, centre])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(reviewer)
    db_session.refresh(centre)

    centre_user = User(
        name="Operator Jaipur",
        email="operator_m8@sih.gov.in",
        password_hash=get_password_hash("OperatorPass123!"),
        role="CENTRE_USER",
        centre_id=centre.id,
    )
    camera = Camera(
        centre_id=centre.id,
        name="Lab 1 Camera",
        source_type="VIDEO_FILE",
        source_url="/storage/videos/sample.mp4",
        is_active=True,
    )
    db_session.add_all([centre_user, camera])
    db_session.commit()
    db_session.refresh(centre_user)
    db_session.refresh(camera)

    session = MonitoringSession(
        centre_id=centre.id,
        camera_id=camera.id,
        physical_attendance=30,
        session_date=date.today(),
        status="PENDING",
        created_by=admin.id,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    reviewer_token = create_access_token({"sub": str(reviewer.id), "email": reviewer.email, "role": "REVIEWER"})
    user_token = create_access_token({"sub": str(centre_user.id), "email": centre_user.email, "role": "CENTRE_USER"})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "reviewer_headers": {"Authorization": f"Bearer {reviewer_token}"},
        "user_headers": {"Authorization": f"Bearer {user_token}"},
        "session": session,
        "centre": centre,
        "camera": camera,
    }


def test_valid_mp4_upload(client, m8_test_setup):
    """1. Upload valid MP4 video and associate with session."""
    session = m8_test_setup["session"]
    video_bytes = generate_test_mp4(num_frames=30, fps=10.0, width=128, height=128)

    files = {"file": ("classroom_test.mp4", BytesIO(video_bytes), "video/mp4")}
    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session.id
    assert data["video_filename"] == "classroom_test.mp4"
    assert data["width"] == 128
    assert data["height"] == 128
    assert data["fps"] == 10.0
    assert data["total_frames"] == 30
    assert data["duration_seconds"] == 3.0
    assert data["video_processing_status"] == "NOT_STARTED"


def test_reject_invalid_file_extension(client, m8_test_setup):
    """2. Reject non-MP4 files."""
    session = m8_test_setup["session"]
    files = {"file": ("test.txt", BytesIO(b"not a video file"), "text/plain")}
    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )
    assert res.status_code == 400
    assert "Only .mp4 files are accepted" in res.json()["detail"]


def test_upload_missing_session(client, m8_test_setup):
    """3. Reject upload for non-existent session."""
    video_bytes = generate_test_mp4(num_frames=10)
    files = {"file": ("test.mp4", BytesIO(video_bytes), "video/mp4")}
    res = client.post(
        "/api/v1/monitoring/sessions/999999/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_unauthorized_upload(client, m8_test_setup):
    """4. Enforce authorization on video upload."""
    session = m8_test_setup["session"]
    video_bytes = generate_test_mp4(num_frames=10)

    # 4a. Unauthenticated blocked (401)
    files = {"file": ("test.mp4", BytesIO(video_bytes), "video/mp4")}
    res_unauth = client.post(f"/api/v1/monitoring/sessions/{session.id}/video", files=files)
    assert res_unauth.status_code == 401

    # 4b. Reviewer read-only blocked (403)
    files = {"file": ("test.mp4", BytesIO(video_bytes), "video/mp4")}
    res_rev = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["reviewer_headers"],
        files=files,
    )
    assert res_rev.status_code == 403


def test_video_metadata_extraction(client, m8_test_setup, db_session):
    """5. Verify OpenCV video metadata is correctly stored on the session record."""
    session = m8_test_setup["session"]
    # 50 frames at 25 fps = 2.0 seconds
    video_bytes = generate_test_mp4(num_frames=50, fps=25.0, width=160, height=120)

    files = {"file": ("lab_inspection.mp4", BytesIO(video_bytes), "video/mp4")}
    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )
    assert res.status_code == 200

    db_session.refresh(session)
    assert session.video_width == 160
    assert session.video_height == 120
    assert session.video_fps == 25.0
    assert session.video_total_frames == 50
    assert session.video_duration_seconds == 2.0
    assert session.video_file_path is not None
    assert os.path.exists(session.video_file_path)


def test_initial_and_periodic_snapshot_extraction(client, m8_test_setup):
    """6, 7, 8. Extract initial snapshot at 00:00 and periodic frames with expected counts."""
    session = m8_test_setup["session"]
    # 40 frames at 10 fps = 4.0 seconds duration
    video_bytes = generate_test_mp4(num_frames=40, fps=10.0, width=64, height=64)

    # Upload video
    files = {"file": ("inspection.mp4", BytesIO(video_bytes), "video/mp4")}
    client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )

    # Process video with 1-second interval
    # At duration 4.0s with interval 1.0s:
    # Timestamps: 0.0s (initial), 1.0s, 2.0s, 3.0s => 4 snapshots
    proc_res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/process-video",
        headers=m8_test_setup["admin_headers"],
        json={"interval_seconds": 1, "max_snapshots": 10},
    )
    assert proc_res.status_code == 200
    data = proc_res.json()
    assert data["session_id"] == session.id
    assert data["video_processing_status"] == "COMPLETED"
    assert data["snapshots_created"] >= 3
    assert len(data["snapshots"]) >= 3

    # Check initial snapshot is at 0.0s (Requirement §7)
    initial_snap = data["snapshots"][0]
    assert initial_snap["sequence_number"] == 1
    assert initial_snap["frame_time_seconds"] == 0.0
    assert initial_snap["processing_status"] == "PENDING"
    assert initial_snap["width"] == 64
    assert initial_snap["height"] == 64


def test_snapshot_database_records(client, m8_test_setup, db_session):
    """9. Verify Snapshot records in MySQL database."""
    session = m8_test_setup["session"]
    video_bytes = generate_test_mp4(num_frames=20, fps=10.0)

    files = {"file": ("test_db.mp4", BytesIO(video_bytes), "video/mp4")}
    client.post(f"/api/v1/monitoring/sessions/{session.id}/video", headers=m8_test_setup["admin_headers"], files=files)
    client.post(
        f"/api/v1/monitoring/sessions/{session.id}/process-video",
        headers=m8_test_setup["admin_headers"],
        json={"interval_seconds": 1},
    )

    db_snapshots = (
        db_session.query(Snapshot)
        .filter(Snapshot.monitoring_session_id == session.id)
        .order_by(Snapshot.sequence_number.asc())
        .all()
    )
    assert len(db_snapshots) >= 2
    for s in db_snapshots:
        assert s.processing_status == "PENDING"
        assert os.path.exists(s.file_path)


def test_reject_corrupted_video(client, m8_test_setup):
    """10. Reject corrupted or non-video binary file uploaded with .mp4 extension."""
    session = m8_test_setup["session"]
    fake_bytes = b"This is a fake header that is not a valid playable MP4."

    files = {"file": ("corrupt.mp4", BytesIO(fake_bytes), "video/mp4")}
    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/video",
        headers=m8_test_setup["admin_headers"],
        files=files,
    )
    assert res.status_code == 400
    assert "Video validation failed" in res.json()["detail"] or "not a valid playable" in res.json()["detail"]


def test_reject_process_video_without_upload(client, m8_test_setup):
    """11. Reject process-video when no video was uploaded."""
    session = m8_test_setup["session"]
    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/process-video",
        headers=m8_test_setup["admin_headers"],
    )
    assert res.status_code == 400
    assert "No uploaded video file found" in res.json()["detail"]


def test_secure_snapshot_access_and_image_stream(client, m8_test_setup):
    """12. Securely retrieve snapshot image content."""
    session = m8_test_setup["session"]
    video_bytes = generate_test_mp4(num_frames=20, fps=10.0)

    files = {"file": ("stream.mp4", BytesIO(video_bytes), "video/mp4")}
    client.post(f"/api/v1/monitoring/sessions/{session.id}/video", headers=m8_test_setup["admin_headers"], files=files)
    proc_res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/process-video",
        headers=m8_test_setup["admin_headers"],
        json={"interval_seconds": 1},
    )
    snap_id = proc_res.json()["snapshots"][0]["id"]

    # Retrieve snapshot image
    img_res = client.get(
        f"/api/v1/monitoring/snapshots/{snap_id}/image",
        headers=m8_test_setup["admin_headers"],
    )
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/jpeg"
    assert len(img_res.content) > 0


def test_path_traversal_protection(client, m8_test_setup, db_session):
    """13. Prevent path traversal attempts when accessing snapshot images."""
    session = m8_test_setup["session"]

    # Create a malicious snapshot record with a path traversal target
    malicious_snapshot = Snapshot(
        monitoring_session_id=session.id,
        file_path="/etc/passwd",
        sequence_number=999,
        processing_status="PENDING",
    )
    db_session.add(malicious_snapshot)
    db_session.commit()
    db_session.refresh(malicious_snapshot)

    res = client.get(
        f"/api/v1/monitoring/snapshots/{malicious_snapshot.id}/image",
        headers=m8_test_setup["admin_headers"],
    )
    assert res.status_code in [403, 404]


def test_processing_failure_handling(client, m8_test_setup, db_session):
    """14. Handle processing errors gracefully by setting video_processing_status=FAILED."""
    session = m8_test_setup["session"]

    # Point session to a deleted or unreadable file
    session.video_file_path = "/storage/nonexistent_video.mp4"
    db_session.commit()

    res = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/process-video",
        headers=m8_test_setup["admin_headers"],
    )
    assert res.status_code == 400
    assert "No uploaded video file found" in res.json()["detail"] or "failed" in res.json()["detail"].lower()
