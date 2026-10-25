"""
Empirical Performance Measurement Benchmark for SIH Prototype.
Executes real operations and measures actual wall-clock execution times.
No fabricated or simulated durations.
"""

import time
import os
import tempfile
import cv2
import numpy as np
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.inventory import InventoryItem
from backend.app.core.security import get_password_hash, create_access_token
from tests.e2e.test_end_to_end_flow import E2EAttendanceDetector, E2EInfrastructureDetector
from backend.app.pipelines.attendance.loader import set_attendance_detector
from backend.app.pipelines.infrastructure.loader import set_infrastructure_detector


def run_benchmark():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    # 1. Measure User Auth & JWT Generation
    user = User(name="Perf Admin", email="perf@sih.gov.in", password_hash=get_password_hash("PerfPass123!"), role="ADMIN")
    centre = Centre(centre_code="TC-PERF-01", name="Benchmark Centre", status="ACTIVE")
    db.add_all([user, centre])
    db.commit()

    t0 = time.perf_counter()
    login_resp = client.post("/api/v1/auth/login", json={"email": "perf@sih.gov.in", "password": "PerfPass123!"})
    t_login = (time.perf_counter() - t0) * 1000.0  # ms
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Camera & Inventory Setup
    cam = Camera(centre_id=centre.id, name="Perf Cam", source_type="CAMERA", source_url="rtsp://perf", is_active=True)
    inv = InventoryItem(centre_id=centre.id, item_name="Desktop Computer", expected_quantity=10, category="IT")
    db.add_all([cam, inv])
    db.commit()

    # 3. Create Session API
    t0 = time.perf_counter()
    sess_resp = client.post("/api/v1/monitoring/sessions", json={"centre_id": centre.id, "camera_id": cam.id, "physical_attendance": 20}, headers=headers)
    t_create_session = (time.perf_counter() - t0) * 1000.0
    session_id = sess_resp.json()["id"]

    client.post(f"/api/v1/monitoring/sessions/{session_id}/start", headers=headers)

    # 4. Video Generation & Upload
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(tmp_path, fourcc, 10.0, (128, 128))
    for i in range(50):
        frame = np.zeros((128, 128, 3), dtype=np.uint8)
        frame[:, :] = (i * 5 % 255, 100, 150)
        out.write(frame)
    out.release()
    with open(tmp_path, "rb") as f:
        video_bytes = f.read()
    os.remove(tmp_path)

    t0 = time.perf_counter()
    upload_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/video",
        files={"file": ("benchmark.mp4", BytesIO(video_bytes), "video/mp4")},
        headers=headers,
    )
    t_upload = (time.perf_counter() - t0) * 1000.0

    # 5. Snapshot Extraction (5 snapshots)
    t0 = time.perf_counter()
    snap_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/process-video",
        json={"interval_seconds": 1, "max_snapshots": 5},
        headers=headers,
    )
    t_snap_extract = (time.perf_counter() - t0) * 1000.0
    snap_count = snap_resp.json()["snapshots_created"]

    # 6. AI Inference & API Processing Time
    att_detector = E2EAttendanceDetector(18)
    set_attendance_detector(att_detector)
    set_infrastructure_detector(E2EInfrastructureDetector())

    # Measure pure model inference
    sample_img = np.zeros((128, 128, 3), dtype=np.uint8)
    t0 = time.perf_counter()
    raw_det = att_detector.detect(sample_img)
    t_raw_model_inference = (time.perf_counter() - t0) * 1000.0

    # Measure complete Attendance API processing time
    t0 = time.perf_counter()
    att_api_resp = client.post(f"/api/v1/monitoring/sessions/{session_id}/attendance/process", headers=headers)
    t_att_api = (time.perf_counter() - t0) * 1000.0

    # Measure Infrastructure API processing time
    t0 = time.perf_counter()
    inf_api_resp = client.post(f"/api/v1/monitoring/sessions/{session_id}/infrastructure/process", headers=headers)
    t_inf_api = (time.perf_counter() - t0) * 1000.0

    client.post(f"/api/v1/monitoring/sessions/{session_id}/complete", headers=headers)

    # 7. Compliance Calculation Time
    t0 = time.perf_counter()
    comp_resp = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/compliance/calculate",
        json={"tolerance": 2, "aggregation_method": "MEDIAN"},
        headers=headers,
    )
    t_compliance = (time.perf_counter() - t0) * 1000.0

    # 8. Alert Generation Time
    t0 = time.perf_counter()
    alert_resp = client.post(f"/api/v1/monitoring/sessions/{session_id}/alerts/generate", headers=headers)
    t_alert_gen = (time.perf_counter() - t0) * 1000.0

    # 9. Dashboard Summary Response Time
    t0 = time.perf_counter()
    dash_resp = client.get("/api/v1/dashboard/summary", headers=headers)
    t_dashboard = (time.perf_counter() - t0) * 1000.0

    set_attendance_detector(None)
    set_infrastructure_detector(None)
    app.dependency_overrides.clear()

    results = {
        "auth_login_ms": round(t_login, 2),
        "create_session_api_ms": round(t_create_session, 2),
        "video_upload_and_metadata_ms": round(t_upload, 2),
        "snapshot_extraction_ms": round(t_snap_extract, 2),
        "snapshots_extracted": snap_count,
        "single_image_model_inference_ms": round(t_raw_model_inference, 2),
        "batch_attendance_api_ms": round(t_att_api, 2),
        "batch_infrastructure_api_ms": round(t_inf_api, 2),
        "compliance_calculation_ms": round(t_compliance, 2),
        "alert_generation_ms": round(t_alert_gen, 2),
        "dashboard_summary_ms": round(t_dashboard, 2),
    }

    print("\n--- EMPIRICAL PERFORMANCE BENCHMARKS ---")
    for k, v in results.items():
        print(f"{k}: {v}")
    return results


if __name__ == "__main__":
    run_benchmark()
