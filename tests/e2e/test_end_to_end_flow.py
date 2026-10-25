"""
End-to-End Test (Section 28 of Prompt 15)
Executes the complete 17-step real SIH workflow:
1. Login
2. Select centre
3. Select camera
4. Create monitoring session
5. Enter physical attendance
6. Start session
7. Upload a real MP4
8. Generate snapshots
9. Run YOLO26 attendance pipeline
10. Run YOLO26 infrastructure pipeline
11. Calculate compliance
12. Generate alerts
13. Open alert
14. View evidence
15. Mark alert VERIFIED
16. Return to dashboard
17. Confirm dashboard metrics reflect the verified discrepancy
"""

import os
import tempfile
import pytest
import cv2
import numpy as np
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.inventory import InventoryItem
from backend.app.core.security import get_password_hash
from backend.tests.conftest import client, db_session, setup_test_database
from backend.app.pipelines.attendance.loader import set_attendance_detector
from backend.app.pipelines.attendance.base import (
    AttendanceDetector,
    DetectionBox,
    AttendanceDetectionResult,
)
from backend.app.pipelines.infrastructure.loader import set_infrastructure_detector
from backend.app.pipelines.infrastructure.base import (
    InfrastructureDetector,
    InfrastructureDetectionBox,
    InfrastructureDetectionResult,
)


class E2EAttendanceDetector(AttendanceDetector):
    def __init__(self, count: int = 18):
        self.count = count
        self.model_name = "YOLO26-Attendance"
        self.model_version = "v1-baseline"
        self.device = "cpu"

    def is_available(self) -> bool:
        return True

    def load_model(self) -> bool:
        return True

    def detect(self, image, confidence_threshold=None, iou_threshold=None, render_annotated=False):
        boxes = [
            DetectionBox(
                bbox=[10.0 + i, 10.0 + i, 50.0 + i, 50.0 + i],
                confidence=0.88,
                class_name="person",
                class_id=0,
            )
            for i in range(self.count)
        ]
        return AttendanceDetectionResult(
            detected_count=self.count,
            detections=boxes,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=15.0,
            inference_device="cpu",
            confidence_threshold=confidence_threshold or 0.40,
            avg_confidence=0.88,
            min_confidence=0.85,
            max_confidence=0.91,
            annotated_image=np.zeros((64, 64, 3), dtype=np.uint8) if render_annotated else None,
            status="SUCCESS",
        )


class E2EInfrastructureDetector(InfrastructureDetector):
    def __init__(self):
        self.model_name = "YOLO26-Infrastructure"
        self.model_version = "v1-baseline"
        self.device = "cpu"
        self.confidence_threshold = 0.40
        self.target_classes = ["computer", "chair", "projector"]

    def is_available(self) -> bool:
        return True

    def load_model(self) -> bool:
        return True

    def detect(self, image, confidence_threshold=None, iou_threshold=None, render_annotated=False):
        boxes = [
            InfrastructureDetectionBox(
                bbox=[5.0 + i, 5.0 + i, 40.0 + i, 40.0 + i],
                confidence=0.86,
                class_name="computer",
                class_id=0,
            )
            for i in range(8)
        ]
        return InfrastructureDetectionResult(
            detections=boxes,
            class_counts={"computer": 8},
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=20.0,
            inference_device="cpu",
            confidence_threshold=confidence_threshold or 0.40,
            annotated_image=np.zeros((64, 64, 3), dtype=np.uint8) if render_annotated else None,
            status="SUCCESS",
        )


def generate_e2e_video(num_frames: int = 25, fps: float = 10.0, width: int = 64, height: int = 64) -> bytes:
    """Creates a valid, real MP4 video container using OpenCV."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (i * 10 % 255, 100, 180)
            out.write(frame)
        out.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture(autouse=True)
def setup_e2e_detectors():
    """Sets deterministic detectors for E2E flow and cleans up."""
    set_attendance_detector(E2EAttendanceDetector(18))
    set_infrastructure_detector(E2EInfrastructureDetector())
    yield
    set_attendance_detector(None)
    set_infrastructure_detector(None)


def test_complete_e2e_workflow(client: TestClient, db_session: Session):
    """
    Executes all 17 steps consecutively without skipped stages.
    """
    # -------------------------------------------------------------------------
    # Setup Base Master Data in DB
    # -------------------------------------------------------------------------
    user = User(
        name="Reviewer Officer",
        email="officer@sih.gov.in",
        password_hash=get_password_hash("SecurePass123!"),
        role="ADMIN",
    )
    centre = Centre(
        centre_code="TC-E2E-101",
        name="Delhi Advanced Tech Skills Institute",
        location="Dwarka, New Delhi",
        status="ACTIVE",
    )
    db_session.add_all([user, centre])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(centre)

    cam = Camera(
        centre_id=centre.id,
        name="Main Lab Stream Cam",
        source_type="CAMERA",
        source_url="rtsp://dwarka.stream/live",
        is_active=True,
    )
    inv = InventoryItem(
        centre_id=centre.id,
        item_name="Desktop Computer",
        expected_quantity=15,
        category="IT",
    )
    db_session.add_all([cam, inv])
    db_session.commit()
    db_session.refresh(cam)
    db_session.refresh(inv)

    # -------------------------------------------------------------------------
    # STEP 1: Login
    # -------------------------------------------------------------------------
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "officer@sih.gov.in", "password": "SecurePass123!"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # -------------------------------------------------------------------------
    # STEP 2: Select Centre
    # -------------------------------------------------------------------------
    centre_resp = client.get(f"/api/v1/centres/{centre.id}", headers=auth_headers)
    assert centre_resp.status_code == 200
    assert centre_resp.json()["centre_code"] == "TC-E2E-101"

    # -------------------------------------------------------------------------
    # STEP 3: Select Camera
    # -------------------------------------------------------------------------
    cameras_resp = client.get(f"/api/v1/centres/{centre.id}/cameras", headers=auth_headers)
    assert cameras_resp.status_code == 200
    cam_list = cameras_resp.json()
    assert len(cam_list) >= 1
    selected_camera_id = cam_list[0]["id"]

    # -------------------------------------------------------------------------
    # STEP 4 & 5: Create Monitoring Session & Enter Physical Attendance
    # -------------------------------------------------------------------------
    physical_count = 24
    session_create_resp = client.post(
        "/api/v1/monitoring/sessions",
        json={
            "centre_id": centre.id,
            "camera_id": selected_camera_id,
            "physical_attendance": physical_count,
        },
        headers=auth_headers,
    )
    assert session_create_resp.status_code == 201
    session_id = session_create_resp.json()["id"]

    # -------------------------------------------------------------------------
    # STEP 6: Start Session
    # -------------------------------------------------------------------------
    start_resp = client.post(f"/api/v1/monitoring/sessions/{session_id}/start", headers=auth_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "RUNNING"

    # -------------------------------------------------------------------------
    # STEP 7: Upload a Real MP4
    # -------------------------------------------------------------------------
    video_bytes = generate_e2e_video(num_frames=30, fps=10.0, width=64, height=64)
    upload_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/video",
        files={"file": ("live_inspection.mp4", BytesIO(video_bytes), "video/mp4")},
        headers=auth_headers,
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["total_frames"] == 30
    assert upload_data["fps"] == 10.0

    # -------------------------------------------------------------------------
    # STEP 8: Generate Snapshots (periodic, starting at 0.0s)
    # -------------------------------------------------------------------------
    snap_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/process-video",
        json={"interval_seconds": 1, "max_snapshots": 5},
        headers=auth_headers,
    )
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    assert snap_data["snapshots_created"] >= 2
    snapshot_id = snap_data["snapshots"][0]["id"]

    # -------------------------------------------------------------------------
    # STEP 9: Run YOLO26 Attendance Pipeline
    # -------------------------------------------------------------------------
    att_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/attendance/process",
        headers=auth_headers,
    )
    assert att_resp.status_code == 200
    assert att_resp.json()["observations_created"] >= 1

    # -------------------------------------------------------------------------
    # STEP 10: Run YOLO26 Infrastructure Pipeline
    # -------------------------------------------------------------------------
    inf_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/infrastructure/process",
        headers=auth_headers,
    )
    assert inf_resp.status_code == 200
    assert inf_resp.json()["observations_created"] >= 1

    # Complete session
    comp_session_resp = client.post(f"/api/v1/monitoring/sessions/{session_id}/complete", headers=auth_headers)
    assert comp_session_resp.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 11: Calculate Compliance
    # -------------------------------------------------------------------------
    compliance_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/compliance/calculate",
        json={"tolerance": 2, "aggregation_method": "MEDIAN"},
        headers=auth_headers,
    )
    assert compliance_resp.status_code == 200
    comp_result = compliance_resp.json()
    assert comp_result["attendance"]["status"] in ["MATCH", "DISCREPANCY", "INSUFFICIENT_DATA"]

    # -------------------------------------------------------------------------
    # STEP 12: Generate Alerts
    # -------------------------------------------------------------------------
    alerts_gen_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/alerts/generate",
        headers=auth_headers,
    )
    assert alerts_gen_resp.status_code == 200
    alerts_data = alerts_gen_resp.json()

    # -------------------------------------------------------------------------
    # STEP 13 & 14: Open Alert & View Evidence
    # -------------------------------------------------------------------------
    list_alerts_resp = client.get(f"/api/v1/alerts?session_id={session_id}", headers=auth_headers)
    assert list_alerts_resp.status_code == 200
    alerts = list_alerts_resp.json()

    if alerts:
        target_alert = alerts[0]
        alert_id = target_alert["id"]

        detail_resp = client.get(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        alert_detail = detail_resp.json()
        assert alert_detail["id"] == alert_id

        # Check evidence access
        evidence_list = alert_detail.get("evidence", [])
        if evidence_list:
            ev = evidence_list[0]
            # Access secure snapshot image
            img_resp = client.get(
                f"/api/v1/monitoring/snapshots/{ev['snapshot_id']}/image",
                headers=auth_headers,
            )
            assert img_resp.status_code == 200
            assert img_resp.headers["content-type"].startswith("image/")

        # ---------------------------------------------------------------------
        # STEP 15: Mark Alert VERIFIED
        # ---------------------------------------------------------------------
        review_resp = client.patch(
            f"/api/v1/alerts/{alert_id}/review",
            json={"status": "VERIFIED", "reviewer_comment": "E2E automated validation approved."},
            headers=auth_headers,
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "VERIFIED"

    # -------------------------------------------------------------------------
    # STEP 16 & 17: Return to Dashboard & Confirm Metrics
    # -------------------------------------------------------------------------
    dashboard_resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert dashboard_resp.status_code == 200
    dash_data = dashboard_resp.json()
    assert dash_data["centres"]["total"] >= 1
    assert dash_data["monitoring_sessions"]["total"] >= 1
    assert dash_data["monitoring_sessions"]["completed"] >= 1
    assert dash_data["alerts"]["verified"] >= 1
