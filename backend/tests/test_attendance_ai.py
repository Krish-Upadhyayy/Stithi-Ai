"""Unit and Integration Tests for YOLO26 Attendance AI Baseline Pipeline."""

import os
import shutil
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.attendance import AttendanceObservation
from backend.app.pipelines.attendance.base import (
    AttendanceDetector,
    DetectionBox,
    AttendanceDetectionResult,
)
from backend.app.pipelines.attendance.loader import (
    get_attendance_detector,
    set_attendance_detector,
)
from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector


class MockAttendanceDetector(AttendanceDetector):
    """Deterministic mock detector for isolated service and API integration tests."""

    def __init__(self, available: bool = True, mock_count: int = 24):
        self._available = available
        self.mock_count = mock_count
        self.model_name = "YOLO26-Face-Presence"
        self.model_version = "v1-baseline"
        self.device = "cpu"
        self.model_path = "ai_models/test_weights.pt"

    def is_available(self) -> bool:
        return self._available

    def load_model(self) -> bool:
        return self._available

    def detect(
        self,
        image,
        confidence_threshold=None,
        iou_threshold=None,
        render_annotated=False,
    ) -> AttendanceDetectionResult:
        if not self._available:
            return AttendanceDetectionResult(
                detected_count=0,
                status="WEIGHTS_MISSING",
                error_message="Attendance AI model weights not configured or missing.",
            )

        # Generate deterministic detections
        detections = [
            DetectionBox(
                bbox=[10.0 + i * 5, 20.0 + i * 5, 50.0 + i * 5, 80.0 + i * 5],
                confidence=0.88,
                class_name="person",
                class_id=0,
            )
            for i in range(self.mock_count)
        ]

        annotated_img = None
        if render_annotated:
            annotated_img = np.zeros((240, 320, 3), dtype=np.uint8)

        return AttendanceDetectionResult(
            detected_count=self.mock_count,
            detections=detections,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=18.5,
            inference_device=self.device,
            confidence_threshold=confidence_threshold or 0.40,
            avg_confidence=0.88,
            min_confidence=0.85,
            max_confidence=0.92,
            annotated_image=annotated_img,
            status="SUCCESS",
        )


@pytest.fixture(autouse=True)
def clean_detector():
    """Ensure global detector is restored after each test."""
    yield
    set_attendance_detector(None)


@pytest.fixture
def auth_headers(db_session: Session):
    """Generates valid JWT bearer authorization headers for an active admin user."""
    user = db_session.query(User).filter(User.email == "test_att_admin@sih.gov.in").first()
    if not user:
        user = User(
            email="test_att_admin@sih.gov.in",
            name="Attendance Admin",
            password_hash="mock_hash",
            role="ADMIN",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_session_with_snapshot(db_session: Session):
    """Sets up a centre, session, snapshot record, and physical image file."""
    centre = Centre(name="AI Test Centre", centre_code="TC-AI-01", location="Tech Hub")
    db_session.add(centre)
    db_session.commit()

    camera = Camera(name="Classroom 1 Cam", centre_id=centre.id, source_type="CCTV", source_url="rtsp://test")
    db_session.add(camera)
    db_session.commit()

    session = MonitoringSession(
        centre_id=centre.id,
        camera_id=camera.id,
        physical_attendance=25,
        status="PENDING",
    )
    db_session.add(session)
    db_session.commit()

    # Create dummy snapshot file in storage
    session_dir = os.path.join(settings.STORAGE_ROOT, settings.SNAPSHOT_DIR, f"session_{session.id}")
    os.makedirs(session_dir, exist_ok=True)
    snap_path = os.path.join(session_dir, "snapshot_000001.jpg")

    dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.imwrite(snap_path, dummy_frame)

    rel_path = os.path.relpath(snap_path, settings.STORAGE_ROOT)
    snapshot = Snapshot(
        monitoring_session_id=session.id,
        file_path=rel_path,
        sequence_number=1,
        frame_time_seconds=0.0,
        width=320,
        height=240,
        processing_status="PENDING",
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    yield session, snapshot

    # Cleanup test files
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)
    evidence_dir = os.path.join(settings.STORAGE_ROOT, settings.EVIDENCE_DIR, f"session_{session.id}")
    if os.path.exists(evidence_dir):
        shutil.rmtree(evidence_dir, ignore_errors=True)


def test_model_configuration():
    """Verify attendance AI configuration values load with correct defaults."""
    assert settings.ATTENDANCE_MODEL_FAMILY in ["YOLO26", "Stithi AI"]
    assert settings.ATTENDANCE_MODEL_VERSION in ["v1-baseline", "v26x-precision"]
    assert settings.ATTENDANCE_DEVICE in ["cpu", "cuda", "mps"]


def test_missing_model_handling(client: TestClient, auth_headers: dict, test_session_with_snapshot):
    """When YOLO26 weights file is missing, API returns HTTP 503 without crashing."""
    _, snapshot = test_session_with_snapshot
    set_attendance_detector(MockAttendanceDetector(available=False))

    response = client.post(
        f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance",
        headers=auth_headers,
    )
    assert response.status_code == 503
    data = response.json()
    assert "not configured" in data["detail"].lower() or "missing" in data["detail"].lower()


def test_swappable_detector_interface():
    """Verify that custom detectors implementing AttendanceDetector can be plugged in seamlessly."""
    mock = MockAttendanceDetector(available=True, mock_count=19)
    set_attendance_detector(mock)
    det = get_attendance_detector()
    assert det.is_available() is True
    res = det.detect("dummy_path")
    assert res.detected_count == 19
    assert res.model_name == "YOLO26-Face-Presence"


def test_single_snapshot_inference_and_observation_creation(
    client: TestClient, auth_headers: dict, test_session_with_snapshot, db_session: Session
):
    """Run YOLO26 attendance detection on a snapshot and verify AttendanceObservation record."""
    _, snapshot = test_session_with_snapshot
    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=22))

    response = client.post(
        f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance",
        headers=auth_headers,
        json={"confidence_threshold": 0.45},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observed_count"] == 22
    assert data["detected_count"] == 22
    assert data["snapshot_id"] == snapshot.id
    assert data["model_name"] == "YOLO26-Face-Presence"
    assert data["model_version"] == "v1-baseline"
    assert data["confidence_threshold"] == 0.45
    assert data["inference_time_ms"] == 18.5
    assert data["processing_status"] == "COMPLETED"

    # Verify database persistence
    obs = db_session.query(AttendanceObservation).filter(AttendanceObservation.snapshot_id == snapshot.id).first()
    assert obs is not None
    assert obs.observed_count == 22


def test_observation_idempotency_and_update(
    client: TestClient, auth_headers: dict, test_session_with_snapshot, db_session: Session
):
    """Reprocessing the same snapshot updates the existing AttendanceObservation rather than duplicating rows."""
    _, snapshot = test_session_with_snapshot

    # First run
    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=20))
    res1 = client.post(f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance", headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["observed_count"] == 20

    # Second run with different count (e.g., hyperparameter recalibration)
    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=25))
    res2 = client.post(f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["observed_count"] == 25

    # Check total database records: must remain exactly 1 record for this snapshot
    count = db_session.query(AttendanceObservation).filter(AttendanceObservation.snapshot_id == snapshot.id).count()
    assert count == 1


def test_missing_snapshot_returns_404(client: TestClient, auth_headers: dict):
    """Non-existent snapshot returns HTTP 404."""
    set_attendance_detector(MockAttendanceDetector(available=True))
    response = client.post("/api/v1/monitoring/snapshots/99999/attendance", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_missing_image_file_returns_404(client: TestClient, auth_headers: dict, db_session: Session):
    """Snapshot pointing to missing file on disk returns HTTP 404."""
    snap = Snapshot(
        monitoring_session_id=1,
        file_path="snapshots/session_1/ghost_snapshot.jpg",
        sequence_number=99,
    )
    db_session.add(snap)
    db_session.commit()

    set_attendance_detector(MockAttendanceDetector(available=True))
    response = client.post(f"/api/v1/monitoring/snapshots/{snap.id}/attendance", headers=auth_headers)
    assert response.status_code == 404
    assert "not found on disk" in response.json()["detail"].lower()


def test_unauthorized_request_rejected(client: TestClient, test_session_with_snapshot):
    """Unauthenticated requests are rejected with HTTP 401."""
    _, snapshot = test_session_with_snapshot
    response = client.post(f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance")
    assert response.status_code == 401


def test_invalid_confidence_threshold_rejected(
    client: TestClient, auth_headers: dict, test_session_with_snapshot
):
    """Confidence threshold outside [0.01, 1.0] returns HTTP 422."""
    _, snapshot = test_session_with_snapshot
    response = client.post(
        f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance",
        headers=auth_headers,
        json={"confidence_threshold": 1.5},
    )
    assert response.status_code == 422


def test_session_level_batch_processing(
    client: TestClient, auth_headers: dict, test_session_with_snapshot, db_session: Session
):
    """Batch process all snapshots in a monitoring session."""
    session, _ = test_session_with_snapshot

    # Add second snapshot
    snap2 = Snapshot(
        monitoring_session_id=session.id,
        file_path=_.file_path,  # Reuse existing physical file
        sequence_number=2,
        frame_time_seconds=10.0,
    )
    db_session.add(snap2)
    db_session.commit()

    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=23))
    response = client.post(
        f"/api/v1/monitoring/sessions/{session.id}/attendance/process",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["snapshots_processed"] == 2
    assert data["observations_created"] == 2
    assert data["status"] == "COMPLETED"


def test_retrieve_session_observations(
    client: TestClient, auth_headers: dict, test_session_with_snapshot
):
    """Retrieve all attendance observations recorded for a session."""
    session, snapshot = test_session_with_snapshot
    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=18))

    # Run detection
    client.post(f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance", headers=auth_headers)

    # Retrieve
    response = client.get(
        f"/api/v1/monitoring/sessions/{session.id}/attendance/observations",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["observed_count"] == 18
    assert data[0]["model_name"] == "YOLO26-Face-Presence"


def test_secure_annotated_image_stream(
    client: TestClient, auth_headers: dict, test_session_with_snapshot, db_session: Session
):
    """Securely stream annotated evidence image."""
    _, snapshot = test_session_with_snapshot
    set_attendance_detector(MockAttendanceDetector(available=True, mock_count=15))

    post_res = client.post(f"/api/v1/monitoring/snapshots/{snapshot.id}/attendance", headers=auth_headers)
    obs_id = post_res.json()["id"]

    response = client.get(
        f"/api/v1/monitoring/attendance/observations/{obs_id}/annotated",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert len(response.content) > 0


def test_annotated_image_path_traversal_prevention(
    client: TestClient, auth_headers: dict, test_session_with_snapshot, db_session: Session
):
    """Path traversal attempt in annotated image path is blocked with HTTP 403."""
    session, snapshot = test_session_with_snapshot
    obs = AttendanceObservation(
        snapshot_id=snapshot.id,
        monitoring_session_id=session.id,
        observed_count=10,
        model_name="YOLO26-Face-Presence",
        model_version="v1-baseline",
        annotated_image_path="../../etc/passwd",
    )
    db_session.add(obs)
    db_session.commit()
    db_session.refresh(obs)

    response = client.get(
        f"/api/v1/monitoring/attendance/observations/{obs.id}/annotated",
        headers=auth_headers,
    )
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()
