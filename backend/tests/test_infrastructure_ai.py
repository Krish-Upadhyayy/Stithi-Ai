"""Unit & Integration Tests for Prompt 11:
YOLO26 Infrastructure AI Asset Detection & Observation Pipeline.

Verifies:
1. Infrastructure model configuration (separate from attendance).
2. Missing model weights handling (graceful message, zero fabricated detections).
3. Model loading and swappable InfrastructureDetector interface.
4. Single snapshot infrastructure inference.
5. InfrastructureObservation creation and field verification.
6. Duplicate / reprocessing idempotency.
7. Session-level batch processing.
8. Invalid snapshot returns 404.
9. Unauthorized access rejection.
10. Invalid class mapping handling.
11. Inventory-to-class mapping ("Desktop Computer" -> "computer", "Office Chair" -> "chair").
12. Missing AI mapping flagged ("AI detection not configured").
13. Model metadata storage and retrieval.
14. Evaluation utility structure and dataset validation execution.
"""

import os
import shutil
import json
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
from backend.app.models.inventory import InventoryItem
from backend.app.models.infrastructure import InfrastructureObservation
from backend.app.pipelines.infrastructure.base import (
    InfrastructureDetector,
    InfrastructureDetectionBox,
    InfrastructureDetectionResult,
)
from backend.app.pipelines.infrastructure.loader import (
    get_infrastructure_detector,
    set_infrastructure_detector,
)
from backend.app.pipelines.infrastructure.mapping import (
    InventoryClassMapper,
    default_mapper,
)
from scripts.infrastructure.validate_dataset import validate_split, check_leakage


# ==============================================================================
# MOCK INFRASTRUCTURE DETECTOR FOR ISOLATED TESTING
# ==============================================================================

class MockInfrastructureDetector(InfrastructureDetector):
    """Deterministic mock detector for isolated unit and integration tests."""

    def __init__(self, available: bool = True, mock_counts: dict = None):
        self._available = available
        self.mock_counts = mock_counts or {"chair": 12, "computer": 8, "projector": 1}
        self.model_name = "YOLO26-Infrastructure"
        self.model_version = "v1-baseline"
        self.device = "cpu"
        self.confidence_threshold = 0.40
        self.target_classes = ["chair", "computer", "projector", "sewing machine", "workbench"]
        self.model_path = "ai_models/test_infra_weights.pt"

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
    ) -> InfrastructureDetectionResult:
        if not self._available:
            return InfrastructureDetectionResult(
                status="WEIGHTS_MISSING",
                error_message="Infrastructure AI model is not configured.",
            )

        detections = []
        for cls_name, count in self.mock_counts.items():
            for i in range(count):
                detections.append(
                    InfrastructureDetectionBox(
                        bbox=[10.0 + i * 5, 20.0 + i * 5, 60.0 + i * 5, 70.0 + i * 5],
                        confidence=0.88,
                        class_name=cls_name,
                        class_id=0,
                    )
                )

        annotated_img = None
        if render_annotated:
            annotated_img = np.zeros((240, 320, 3), dtype=np.uint8)

        return InfrastructureDetectionResult(
            detections=detections,
            class_counts=dict(self.mock_counts),
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=24.5,
            inference_device=self.device,
            confidence_threshold=confidence_threshold or 0.40,
            annotated_image=annotated_img,
            status="SUCCESS",
        )


@pytest.fixture(autouse=True)
def clean_infrastructure_detector():
    """Ensure global infrastructure detector is restored after each test."""
    yield
    set_infrastructure_detector(None)


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Provides valid Bearer Authorization header for admin user."""
    user = db_session.query(User).filter(User.email == "test_infra_admin@sih.gov.in").first()
    if not user:
        user = User(
            email="test_infra_admin@sih.gov.in",
            name="Infra Admin",
            password_hash="mock_hash",
            role="ADMIN",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def monitoring_fixture_with_snapshots(db_session: Session):
    """Sets up Centre, Camera, Session, InventoryItems, and physical test snapshot images."""
    # 1. Centre & Camera
    centre = Centre(
        name="Skills Hub Infra Test",
        centre_code="INFR01",
        location="Sector 62, Noida",
        status="ACTIVE",
    )
    db_session.add(centre)
    db_session.commit()
    db_session.refresh(centre)

    # Inventory items for mapping
    inv_comp = InventoryItem(centre_id=centre.id, item_name="Desktop Computer", expected_quantity=20)
    inv_chair = InventoryItem(centre_id=centre.id, item_name="Office Chair", expected_quantity=25)
    inv_proj = InventoryItem(centre_id=centre.id, item_name="Projector", expected_quantity=1)
    db_session.add_all([inv_comp, inv_chair, inv_proj])
    db_session.commit()

    camera = Camera(
        centre_id=centre.id,
        name="Lab Camera 1",
        source_url="rtsp://lab1.local/live",
        source_type="CAMERA",
        is_active=True,
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    session = MonitoringSession(
        centre_id=centre.id,
        camera_id=camera.id,
        physical_attendance=25,
        status="RUNNING",
        video_processing_status="COMPLETED",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create real dummy snapshot image on disk
    snap_dir = os.path.join(settings.STORAGE_ROOT, settings.SNAPSHOT_DIR, f"session_{session.id}")
    os.makedirs(snap_dir, exist_ok=True)
    snap_filename = "snap_000001.jpg"
    full_path = os.path.join(snap_dir, snap_filename)
    dummy_img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.imwrite(full_path, dummy_img)

    rel_path = os.path.join(settings.SNAPSHOT_DIR, f"session_{session.id}", snap_filename)
    snapshot = Snapshot(
        monitoring_session_id=session.id,
        file_path=rel_path,
        sequence_number=1,
        frame_time_seconds=10.0,
        width=320,
        height=240,
        processing_status="COMPLETED",
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    yield {
        "centre": centre,
        "camera": camera,
        "session": session,
        "snapshot": snapshot,
        "image_full_path": full_path,
    }

    # Cleanup image on disk
    shutil.rmtree(snap_dir, ignore_errors=True)
    evidence_dir = os.path.join(settings.STORAGE_ROOT, settings.EVIDENCE_DIR, "infrastructure", f"session_{session.id}")
    shutil.rmtree(evidence_dir, ignore_errors=True)


# ==============================================================================
# TESTS
# ==============================================================================

def test_infrastructure_model_configuration():
    """1. Infrastructure model configuration is independent from Attendance AI."""
    assert settings.INFRASTRUCTURE_MODEL_FAMILY in ["YOLO26", "Stithi AI"]
    assert settings.INFRASTRUCTURE_MODEL_TYPE in ["yolo26", "yolo26x"]
    assert settings.INFRASTRUCTURE_CONFIDENCE_THRESHOLD in [0.25, 0.40]
    assert settings.INFRASTRUCTURE_IOU_THRESHOLD == 0.50
    assert settings.INFRASTRUCTURE_DEVICE in ["cpu", "cuda:0", "mps"]
    # Crucial decoupling requirement:
    assert settings.INFRASTRUCTURE_MODEL_PATH != settings.ATTENDANCE_MODEL_PATH


def test_missing_model_weights(client: TestClient, auth_headers: dict, monitoring_fixture_with_snapshots: dict):
    """2. Gracefully handles unconfigured model weights without crashing or fabricating numbers."""
    set_infrastructure_detector(MockInfrastructureDetector(available=False))
    snap_id = monitoring_fixture_with_snapshots["snapshot"].id

    res = client.post(
        f"/api/v1/monitoring/snapshots/{snap_id}/infrastructure",
        headers=auth_headers,
        json={},
    )
    assert res.status_code == 503
    assert "Infrastructure AI model is not configured" in res.json()["detail"]


def test_model_loading():
    """3. Model loading initializes once and exposes availability."""
    detector = MockInfrastructureDetector(available=True)
    assert detector.is_available() is True
    assert detector.load_model() is True


def test_single_snapshot_infrastructure_inference(
    client: TestClient, auth_headers: dict, monitoring_fixture_with_snapshots: dict
):
    """4. Runs YOLO26 infrastructure detection on a single snapshot and returns structured results."""
    set_infrastructure_detector(
        MockInfrastructureDetector(available=True, mock_counts={"chair": 24, "computer": 18, "projector": 1})
    )
    snap = monitoring_fixture_with_snapshots["snapshot"]

    res = client.post(
        f"/api/v1/monitoring/snapshots/{snap.id}/infrastructure",
        headers=auth_headers,
        json={"confidence_threshold": 0.40, "render_annotated": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["snapshot_id"] == snap.id
    assert data["total_detected_assets"] == 43
    assert data["model_name"] == "YOLO26-Infrastructure"
    assert len(data["detections"]) == 3

    counts_by_class = {d["asset_type"]: d["count"] for d in data["detections"]}
    assert counts_by_class == {"chair": 24, "computer": 18, "projector": 1}
    # Apparent visual state:
    for d in data["detections"]:
        assert d["status"] == "Visually detected"


def test_infrastructure_observation_creation(
    client: TestClient, auth_headers: dict, db_session: Session, monitoring_fixture_with_snapshots: dict
):
    """5. Observation records are created in DB with correct session, snapshot, and asset metadata."""
    set_infrastructure_detector(
        MockInfrastructureDetector(available=True, mock_counts={"chair": 15, "computer": 10})
    )
    snap = monitoring_fixture_with_snapshots["snapshot"]

    res = client.post(
        f"/api/v1/monitoring/snapshots/{snap.id}/infrastructure",
        headers=auth_headers,
        json={},
    )
    assert res.status_code == 200

    obs_records = (
        db_session.query(InfrastructureObservation)
        .filter(InfrastructureObservation.snapshot_id == snap.id)
        .all()
    )
    assert len(obs_records) == 2
    for obs in obs_records:
        assert obs.monitoring_session_id == snap.monitoring_session_id
        assert obs.processing_status == "COMPLETED"
        assert obs.model_name == "YOLO26-Infrastructure"
        assert obs.bounding_boxes is not None
        assert obs.detected_quantity in [15, 10]


def test_duplicate_and_reprocessing_idempotency(
    client: TestClient, auth_headers: dict, db_session: Session, monitoring_fixture_with_snapshots: dict
):
    """6. Re-running detection updates/replaces observations idempotently without duplicate record proliferation."""
    set_infrastructure_detector(MockInfrastructureDetector(available=True, mock_counts={"chair": 10}))
    snap = monitoring_fixture_with_snapshots["snapshot"]

    # First run
    res1 = client.post(f"/api/v1/monitoring/snapshots/{snap.id}/infrastructure", headers=auth_headers)
    assert res1.status_code == 200
    count_1 = db_session.query(InfrastructureObservation).filter_by(snapshot_id=snap.id).count()
    assert count_1 == 1

    # Second run with different counts
    set_infrastructure_detector(MockInfrastructureDetector(available=True, mock_counts={"chair": 12, "computer": 5}))
    res2 = client.post(f"/api/v1/monitoring/snapshots/{snap.id}/infrastructure", headers=auth_headers)
    assert res2.status_code == 200
    count_2 = db_session.query(InfrastructureObservation).filter_by(snapshot_id=snap.id).count()
    # Replaces prior snapshot observations; does not duplicate
    assert count_2 == 2


def test_session_level_processing(
    client: TestClient, auth_headers: dict, monitoring_fixture_with_snapshots: dict
):
    """7. Batch processes all session snapshots and returns processing summary."""
    set_infrastructure_detector(MockInfrastructureDetector(available=True, mock_counts={"chair": 20, "computer": 15}))
    session_id = monitoring_fixture_with_snapshots["session"].id

    res = client.post(
        f"/api/v1/monitoring/sessions/{session_id}/infrastructure/process",
        headers=auth_headers,
        json={"confidence_threshold": 0.40},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["snapshots_processed"] == 1
    assert data["observations_created"] == 2
    assert data["detected_summary"] == {"chair": 20, "computer": 15}
    assert data["status"] == "COMPLETED"


def test_invalid_snapshot_returns_404(client: TestClient, auth_headers: dict):
    """8. Querying non-existent snapshot ID returns 404 Not Found."""
    set_infrastructure_detector(MockInfrastructureDetector(available=True))
    res = client.post("/api/v1/monitoring/snapshots/999999/infrastructure", headers=auth_headers)
    assert res.status_code == 404


def test_unauthorized_access_rejected(client: TestClient, monitoring_fixture_with_snapshots: dict):
    """9. Missing authorization credentials returns 401 Unauthorized."""
    snap_id = monitoring_fixture_with_snapshots["snapshot"].id
    res = client.post(f"/api/v1/monitoring/snapshots/{snap_id}/infrastructure")
    assert res.status_code == 401


def test_invalid_class_mapping():
    """10. Unmapped or unknown classes are not erroneously mapped."""
    mapper = InventoryClassMapper(supported_classes=["chair", "computer"])
    assert mapper.map_inventory_to_class("Tractor") is None
    assert mapper.map_inventory_to_class("Unknown Asset") is None


def test_inventory_to_class_mapping():
    """11. Configurable mapping resolves common inventory variations into canonical AI classes."""
    mapper = default_mapper
    assert mapper.map_inventory_to_class("Desktop Computer") == "computer"
    assert mapper.map_inventory_to_class("HP PC Workstation") == "computer"
    assert mapper.map_inventory_to_class("Student Chair") == "chair"
    assert mapper.map_inventory_to_class("Office Revolving Chair") == "chair"
    assert mapper.map_inventory_to_class("Multimedia Projector") == "projector"
    assert mapper.map_inventory_to_class("Industrial Sewing Machine") == "sewing machine"
    assert mapper.map_inventory_to_class("Electronics Workbench") == "workbench"


def test_missing_ai_mapping_flagged():
    """12. Items with no trained detector are explicitly flagged as 'AI detection not configured'."""
    mapper = default_mapper
    assert mapper.get_status_for_item("Welding Torch") == "AI detection not configured"
    assert mapper.get_status_for_item("Safety Goggles") == "AI detection not configured"
    assert mapper.get_status_for_item("Blackboard") == "AI detection not configured"
    assert "Configured" in mapper.get_status_for_item("Desktop Computer")


def test_model_metadata_storage(client: TestClient, auth_headers: dict):
    """13. API endpoint returns active infrastructure model metadata."""
    set_infrastructure_detector(MockInfrastructureDetector(available=True))
    res = client.get("/api/v1/ai/infrastructure/model-info", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "YOLO26-Infrastructure"
    assert data["model_version"] == "v1-baseline"
    assert data["is_available"] is True
    assert "chair" in data["target_classes"]
    assert "computer" in data["target_classes"]


def test_evaluation_utility_structure(tmp_path):
    """14. Dataset validation utility operates properly on empty or populated split structures."""
    # Test on empty dataset directory
    split_dir = tmp_path / "test"
    (split_dir / "images").mkdir(parents=True)
    (split_dir / "labels").mkdir(parents=True)

    rep = validate_split(str(tmp_path), "test")
    assert rep["is_valid"] is True
    assert rep["total_images"] == 0
    assert rep["total_objects"] == 0

    leakage = check_leakage(str(tmp_path))
    assert len(leakage) == 0
