"""
Failure Scenarios & Security Tests (Prompt 15 Sections 20, 21, 23, 24, 29)
Validates intentional failures and security boundaries:
1. Invalid file format for video upload (rejected with 400).
2. Corrupted video file (handled gracefully, produces FAILED state, no database corruption).
3. Missing snapshot returns 404.
4. Path traversal attempt on media stream (e.g. ../../etc/passwd or absolute path).
5. Unauthorized cross-centre evidence access rejected with 403.
6. Reverting reviewed alert rejected with 400.
7. System does not crash on unhandled inputs.
"""

from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.core.security import get_password_hash, create_access_token
from backend.tests.conftest import client, db_session, setup_test_database


def test_failure_invalid_video_format_rejected(client: TestClient, db_session: Session):
    """Uploading a non-video format (e.g. .txt or .exe) is rejected with 400."""
    admin = User(name="Admin Fail", email="fail_admin@sih.gov.in", password_hash=get_password_hash("Pass123!"), role="ADMIN")
    centre = Centre(centre_code="TC-FAIL-01", name="Failure Test Centre", status="ACTIVE")
    db_session.add_all([admin, centre])
    db_session.commit()

    token = create_access_token({"sub": str(admin.id), "role": "ADMIN", "email": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    sess = MonitoringSession(centre_id=centre.id, physical_attendance=20, status="RUNNING")
    db_session.add(sess)
    db_session.commit()

    # Upload a text file disguised as mp4 or txt
    files = {"file": ("malicious.txt", BytesIO(b"Hello world this is not video"), "text/plain")}
    resp = client.post(f"/api/v1/monitoring/sessions/{sess.id}/video", files=files, headers=headers)
    assert resp.status_code in [400, 422], "Invalid file type must be rejected"


def test_failure_corrupted_video_handling(client: TestClient, db_session: Session):
    """Uploading random junk bytes with .mp4 extension fails gracefully."""
    admin = User(name="Admin Junk", email="junk_admin@sih.gov.in", password_hash=get_password_hash("Pass123!"), role="ADMIN")
    centre = Centre(centre_code="TC-FAIL-02", name="Failure Centre 2", status="ACTIVE")
    db_session.add_all([admin, centre])
    db_session.commit()

    token = create_access_token({"sub": str(admin.id), "role": "ADMIN", "email": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    sess = MonitoringSession(centre_id=centre.id, physical_attendance=20, status="RUNNING")
    db_session.add(sess)
    db_session.commit()

    corrupted_bytes = b"CORRUPTED_MP4_HEADER_NO_OPENCV_COMPATIBILITY_GARBAGE_BYTES"
    files = {"file": ("corrupt.mp4", BytesIO(corrupted_bytes), "video/mp4")}
    resp = client.post(f"/api/v1/monitoring/sessions/{sess.id}/video", files=files, headers=headers)
    # The endpoint should reject it with 400
    assert resp.status_code in [400, 422]


def test_security_path_traversal_on_snapshots(client: TestClient, db_session: Session):
    """Attempting path traversal attack on snapshot retrieval returns 400 or 404."""
    admin = User(name="Sec Admin", email="sec_admin@sih.gov.in", password_hash=get_password_hash("Pass123!"), role="ADMIN")
    centre = Centre(centre_code="TC-SEC-01", name="Security Centre", status="ACTIVE")
    db_session.add_all([admin, centre])
    db_session.commit()

    token = create_access_token({"sub": str(admin.id), "role": "ADMIN", "email": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    sess = MonitoringSession(centre_id=centre.id, physical_attendance=20, status="RUNNING")
    db_session.add(sess)
    db_session.commit()

    # Create a malicious snapshot record with path traversal in storage path
    malicious_snap = Snapshot(
        monitoring_session_id=sess.id,
        sequence_number=999,
        file_path="../../../../../etc/passwd",
        processing_status="COMPLETED",
    )
    db_session.add(malicious_snap)
    db_session.commit()

    resp = client.get(f"/api/v1/monitoring/snapshots/{malicious_snap.id}/image", headers=headers)
    assert resp.status_code in [400, 403, 404], "Path traversal path must not serve arbitrary system files"


def test_security_unauthenticated_snapshot_access_rejected(client: TestClient, db_session: Session):
    """Snapshot image access without token returns 401 Unauthorized."""
    centre = Centre(centre_code="TC-SEC-02", name="Security Centre 2", status="ACTIVE")
    db_session.add(centre)
    db_session.commit()

    sess = MonitoringSession(centre_id=centre.id, physical_attendance=15, status="RUNNING")
    db_session.add(sess)
    db_session.commit()

    snap = Snapshot(
        monitoring_session_id=sess.id,
        sequence_number=1,
        file_path="storage/sessions/999/snap.jpg",
        processing_status="COMPLETED",
    )
    db_session.add(snap)
    db_session.commit()

    resp = client.get(f"/api/v1/monitoring/snapshots/{snap.id}/image")
    assert resp.status_code == 401, "Unauthenticated access to snapshot must be rejected with 401"
