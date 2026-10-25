"""Comprehensive Unit & Pipeline Tests for Prompt 10:
YOLO26 Attendance Dataset, Fine-Tuning & Evaluation Workflow.

Tests verify:
1. Dataset validation.
2. Invalid annotations (malformed, out-of-bounds, degenerate, disallowed classes).
3. Dataset split validation (train/val/test pairing and presence).
4. Train/test leakage prevention (duplicate files & session prefix sequence leakage).
5. Baseline evaluation pipeline.
6. Fine-tuned evaluation pipeline & comparative delta calculation.
7. Count MAE calculation.
8. Exact-count match percentage calculation.
9. +/-1 and +/-2 headcount tolerance metrics.
10. Model registry registration and metadata structure.
11. Model configuration loading.
12. Evaluation result persistence.
13. Production model loading (priority over default config).
14. Missing model handling (graceful status, zero fabricated metrics).
"""

import os
import json
import shutil
import tempfile
import pytest
import numpy as np
from PIL import Image

from backend.app.core.config import settings
from backend.app.pipelines.attendance.base import (
    AttendanceDetector,
    DetectionBox,
    AttendanceDetectionResult,
)
from backend.app.pipelines.attendance.loader import (
    get_attendance_detector,
    set_attendance_detector,
)
from backend.app.ml.attendance.count_metrics import (
    ImageCountEvaluation,
    AttendanceCountEvaluator,
    AttendanceCountMetricsReport,
)
from backend.app.ml.attendance.dataset_validator import (
    DatasetValidator,
    DatasetValidationReport,
)
from backend.app.ml.attendance.evaluator import (
    AttendanceModelEvaluator,
    compute_iou,
)
from backend.app.ml.attendance.registry import AttendanceModelRegistry
from backend.app.ml.attendance.error_analysis import AttendanceErrorAnalyzer


# ==============================================================================
# TEST FIXTURES & MOCK DETECTORS
# ==============================================================================

class DeterministicTestDetector(AttendanceDetector):
    """Deterministic detector for unit tests without GPU/large model dependencies."""

    def __init__(self, pred_boxes_map=None, mock_count=5):
        self.pred_boxes_map = pred_boxes_map or {}
        self.mock_count = mock_count
        self.model_name = "YOLO26-Attendance-Test"
        self.model_version = "v1-test"
        self.confidence_threshold = 0.40
        self.device = "cpu"
        self.model_path = "test_weights.pt"

    def is_available(self) -> bool:
        return True

    def load_model(self) -> bool:
        return True

    def detect(self, image, confidence_threshold=None, iou_threshold=None, render_annotated=False):
        img_name = os.path.basename(image) if isinstance(image, str) else "sample.jpg"
        boxes = self.pred_boxes_map.get(img_name, [])
        count = len(boxes) if img_name in self.pred_boxes_map else self.mock_count

        detections = [
            DetectionBox(
                bbox=b,
                confidence=0.90,
                class_name="person",
                class_id=0,
            )
            for b in boxes
        ]

        return AttendanceDetectionResult(
            detected_count=count,
            detections=detections,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=12.0,
            inference_device=self.device,
            confidence_threshold=confidence_threshold or 0.40,
            avg_confidence=0.90,
            status="SUCCESS",
        )


@pytest.fixture
def temp_dataset_dir():
    """Creates a temporary synthetic dataset structure for tests."""
    temp_dir = tempfile.mkdtemp(prefix="sih_test_dataset_")
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(temp_dir, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, split, "labels"), exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_registry_dir(monkeypatch):
    """Sets a temporary registry root to avoid modifying production models."""
    temp_dir = tempfile.mkdtemp(prefix="sih_test_registry_")
    prod_dir = os.path.join(temp_dir, "production")
    meta_file = os.path.join(prod_dir, "model_metadata.json")
    monkeypatch.setattr("backend.app.ml.attendance.registry.REGISTRY_ROOT", temp_dir)
    monkeypatch.setattr("backend.app.ml.attendance.registry.PRODUCTION_DIR", prod_dir)
    monkeypatch.setattr("backend.app.ml.attendance.registry.METADATA_FILE", meta_file)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# TESTS 1 & 2: DATASET VALIDATION & INVALID ANNOTATIONS
# ==============================================================================

def test_dataset_validation_valid_structure(temp_dataset_dir):
    """1. Dataset validation passes when clean YOLO annotations and images match."""
    # Create valid synthetic image and label
    img_path = os.path.join(temp_dataset_dir, "train", "images", "session1_snap001.jpg")
    lbl_path = os.path.join(temp_dataset_dir, "train", "labels", "session1_snap001.txt")

    img = Image.new("RGB", (640, 480), color=(100, 100, 100))
    img.save(img_path)

    # Valid YOLO format: class_id xc yc w h
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("0 0.50 0.50 0.20 0.30\n")
        f.write("0 0.25 0.30 0.15 0.25\n")

    validator = DatasetValidator(temp_dataset_dir)
    report = validator.validate_split("train")

    assert report.is_valid is True
    assert report.total_images == 1
    assert report.annotated_images == 1
    assert report.total_objects == 2
    assert report.avg_objects_per_image == 2.0
    assert report.class_distribution == {0: 2}
    assert len(report.issues) == 0


def test_dataset_validation_invalid_annotations(temp_dataset_dir):
    """2. Dataset validator detects malformed, out-of-bounds, degenerate, and disallowed class labels."""
    img_path = os.path.join(temp_dataset_dir, "train", "images", "session1_snap002.jpg")
    lbl_path = os.path.join(temp_dataset_dir, "train", "labels", "session1_snap002.txt")

    img = Image.new("RGB", (640, 480), color=(120, 120, 120))
    img.save(img_path)

    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("0 0.5 0.5\n")                       # Issue: malformed tuple (3 tokens instead of 5)
        f.write("0 1.25 0.5 0.2 0.3\n")               # Issue: xc > 1.0 out of bounds
        f.write("0 0.5 0.5 0.0 0.3\n")                # Issue: w=0 degenerate box
        f.write("5 0.4 0.4 0.2 0.2\n")                # Issue: class 5 not in allowed set {0}
        f.write("0 abc 0.5 0.2 0.2\n")                # Issue: non-numeric coordinate

    validator = DatasetValidator(temp_dataset_dir, allowed_classes={0})
    report = validator.validate_split("train")

    assert report.is_valid is False
    issue_types = {issue.issue_type for issue in report.issues}
    assert "MALFORMED_YOLO_TUPLE" in issue_types
    assert "OUT_OF_BOUNDS_COORDINATE" in issue_types
    assert "DEGENERATE_BOX" in issue_types
    assert "DISALLOWED_CLASS_ID" in issue_types
    assert "NON_NUMERIC_COORDINATE" in issue_types


# ==============================================================================
# TESTS 3 & 4: SPLIT VALIDATION & DATA LEAKAGE DETECTION
# ==============================================================================

def test_dataset_split_validation(temp_dataset_dir):
    """3. Tests split validation across train, val, and test partitions including missing labels."""
    # Put image in 'val' with missing label
    val_img = os.path.join(temp_dataset_dir, "val", "images", "val_img01.png")
    Image.new("RGB", (320, 240)).save(val_img)

    validator = DatasetValidator(temp_dataset_dir)
    res = validator.validate_full_dataset()

    assert res["val"]["total_images"] == 1
    assert res["val"]["missing_labels"] == 1
    assert res["val"]["is_valid"] is False
    assert res["dataset_valid"] is False


def test_data_leakage_detection(temp_dataset_dir):
    """4. Detects critical file overlap and temporal sequence leakage between train and test splits."""
    # 1. Critical leakage: Identical image filename in train and test
    train_img = os.path.join(temp_dataset_dir, "train", "images", "camera1_frame100.jpg")
    test_img = os.path.join(temp_dataset_dir, "test", "images", "camera1_frame100.jpg")
    Image.new("RGB", (100, 100)).save(train_img)
    Image.new("RGB", (100, 100)).save(test_img)

    # 2. Sequence prefix leakage: Same video session prefix in train and test
    train_seq = os.path.join(temp_dataset_dir, "train", "images", "session_99_snap1.jpg")
    test_seq = os.path.join(temp_dataset_dir, "test", "images", "session_99_snap2.jpg")
    Image.new("RGB", (100, 100)).save(train_seq)
    Image.new("RGB", (100, 100)).save(test_seq)

    validator = DatasetValidator(temp_dataset_dir)
    warnings = validator.check_leakage_between_splits()

    assert any("CRITICAL LEAKAGE" in w and "camera1_frame100" in w for w in warnings)
    assert any("SEQUENCE LEAKAGE" in w and "session_99" in w for w in warnings)


# ==============================================================================
# TESTS 5 & 6: BASELINE & FINE-TUNED EVALUATION PIPELINE
# ==============================================================================

def test_baseline_evaluation_pipeline(temp_dataset_dir):
    """5. Evaluates detector on test split and computes precision, recall, mAP, and speed."""
    img_name = "test_frame_01.jpg"
    img_path = os.path.join(temp_dataset_dir, "test", "images", img_name)
    lbl_path = os.path.join(temp_dataset_dir, "test", "labels", "test_frame_01.txt")

    Image.new("RGB", (640, 480)).save(img_path)
    # Ground truth: 2 individuals at known normalized coordinates
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("0 0.30 0.30 0.20 0.20\n")
        f.write("0 0.70 0.70 0.20 0.20\n")

    # Mock detector predicting 2 matching boxes
    pred_boxes = [
        [0.20, 0.20, 0.40, 0.40],  # xc=0.30, yc=0.30, w=0.20, h=0.20 -> matches GT 1
        [0.60, 0.60, 0.80, 0.80],  # xc=0.70, yc=0.70, w=0.20, h=0.20 -> matches GT 2
    ]
    detector = DeterministicTestDetector(pred_boxes_map={img_name: pred_boxes})
    evaluator = AttendanceModelEvaluator(detector)

    result = evaluator.evaluate_split(temp_dataset_dir, split_name="test")

    assert result["status"] == "SUCCESS"
    assert result["images_evaluated"] == 1
    assert result["detection_metrics"]["precision"] == 1.0
    assert result["detection_metrics"]["recall"] == 1.0
    assert result["detection_metrics"]["map50"] == 1.0
    assert result["count_metrics"]["mae"] == 0.0
    assert result["count_metrics"]["exact_match_pct"] == 100.0


def test_finetuned_evaluation_pipeline_and_comparison():
    """6. Compares baseline vs fine-tuned evaluation reports and calculates exact metric deltas."""
    baseline_eval = {
        "model_name": "YOLO26-Baseline",
        "model_version": "v1-baseline",
        "detection_metrics": {
            "precision": 0.8200,
            "recall": 0.7800,
            "map50": 0.7500,
            "map50_95": 0.5200,
            "false_positives": 18,
            "false_negatives": 22,
        },
        "count_metrics": {
            "mae": 3.40,
            "rmse": 4.10,
            "exact_match_pct": 45.0,
            "within_1_pct": 70.0,
            "within_2_pct": 82.0,
        },
        "speed_metrics": {"avg_inference_time_ms": 22.5},
    }

    finetuned_eval = {
        "model_name": "YOLO26-Attendance-Finetuned",
        "model_version": "v2-finetuned",
        "detection_metrics": {
            "precision": 0.9100,
            "recall": 0.8900,
            "map50": 0.8600,
            "map50_95": 0.6400,
            "false_positives": 8,
            "false_negatives": 11,
        },
        "count_metrics": {
            "mae": 1.10,
            "rmse": 1.50,
            "exact_match_pct": 75.0,
            "within_1_pct": 92.0,
            "within_2_pct": 98.0,
        },
        "speed_metrics": {"avg_inference_time_ms": 21.8},
    }

    comparison = AttendanceModelRegistry.compare_models(baseline_eval, finetuned_eval)
    metrics = comparison["metrics_comparison"]

    assert metrics["count_mae"]["baseline"] == 3.40
    assert metrics["count_mae"]["finetuned"] == 1.10
    assert metrics["count_mae"]["delta"] == -2.30  # MAE improved by 2.30 people
    assert metrics["exact_match_pct"]["delta"] == 30.0
    assert metrics["precision"]["delta"] == 0.09
    assert metrics["recall"]["delta"] == 0.11
    assert "Fine-tuned model demonstrated lower Count MAE" in comparison["recommendation"]


# ==============================================================================
# TESTS 7, 8, 9: HEADCOUNT ERROR METRICS (MAE, EXACT, +/-1, +/-2)
# ==============================================================================

def test_count_mae_calculation():
    """7. Verifies calculation of Mean Absolute Error (MAE) and RMSE on actual vs predicted headcounts."""
    evaluations = [
        ImageCountEvaluation(image_name="img1.jpg", actual_count=30, predicted_count=28),  # error = 2
        ImageCountEvaluation(image_name="img2.jpg", actual_count=20, predicted_count=20),  # error = 0
        ImageCountEvaluation(image_name="img3.jpg", actual_count=15, predicted_count=18),  # error = 3
        ImageCountEvaluation(image_name="img4.jpg", actual_count=0, predicted_count=1),    # error = 1
    ]
    # abs_errors: [2, 0, 3, 1] -> sum = 6 -> MAE = 6 / 4 = 1.5
    # sq_errors: [4, 0, 9, 1] -> sum = 14 -> RMSE = sqrt(14 / 4) = sqrt(3.5) ≈ 1.87
    report = AttendanceCountEvaluator.compute_metrics(evaluations)

    assert report.total_images == 4
    assert report.mae == 1.5
    assert round(report.rmse, 2) == 1.87
    # MAPE on non-zero actuals: (|2|/30 + |0|/20 + |3|/15) / 3 * 100 = (0.0667 + 0 + 0.2) / 3 * 100 = 8.89%
    assert report.mape is not None
    assert round(report.mape, 2) == 8.89


def test_exact_count_calculation():
    """8. Verifies exact headcount match percentage."""
    evaluations = [
        ImageCountEvaluation(image_name="a.jpg", actual_count=10, predicted_count=10),
        ImageCountEvaluation(image_name="b.jpg", actual_count=12, predicted_count=12),
        ImageCountEvaluation(image_name="c.jpg", actual_count=15, predicted_count=14),
        ImageCountEvaluation(image_name="d.jpg", actual_count=20, predicted_count=22),
    ]
    # 2 exact matches out of 4 images = 50.0%
    report = AttendanceCountEvaluator.compute_metrics(evaluations)

    assert report.exact_count == 2
    assert report.exact_match_pct == 50.0


def test_plus_minus_one_and_two_count_metrics():
    """9. Verifies accuracy rates within +/- 1 person and +/- 2 people tolerances."""
    evaluations = [
        ImageCountEvaluation(image_name="1.jpg", actual_count=10, predicted_count=10), # error 0 (within 1, within 2)
        ImageCountEvaluation(image_name="2.jpg", actual_count=10, predicted_count=11), # error 1 (within 1, within 2)
        ImageCountEvaluation(image_name="3.jpg", actual_count=10, predicted_count=12), # error 2 (not within 1, within 2)
        ImageCountEvaluation(image_name="4.jpg", actual_count=10, predicted_count=15), # error 5 (neither)
    ]
    # within_1: 2 / 4 = 50.0%
    # within_2: 3 / 4 = 75.0%
    report = AttendanceCountEvaluator.compute_metrics(evaluations)

    assert report.within_1_pct == 50.0
    assert report.within_2_pct == 75.0
    assert report.overcount_count == 3
    assert report.undercount_count == 0


# ==============================================================================
# TESTS 10, 11, 12: MODEL REGISTRY & EVALUATION PERSISTENCE
# ==============================================================================

def test_model_registry_registration_and_metadata(temp_registry_dir):
    """10. Tests model registry registration, metadata file generation, and weight artifact handling."""
    dummy_weights = os.path.join(temp_registry_dir, "test_exp_best.pt")
    with open(dummy_weights, "wb") as f:
        f.write(b"WEIGHTS_CONTENT")

    metrics_payload = {
        "count_metrics": {"mae": 1.25, "exact_match_pct": 78.0},
        "detection_metrics": {"precision": 0.92, "recall": 0.89},
    }

    meta = AttendanceModelRegistry.register_production_model(
        model_name="YOLO26-Attendance-Prod",
        version="v2-finetuned",
        weights_source_path=dummy_weights,
        metrics=metrics_payload,
        selection_rationale="Achieved lowest Count MAE of 1.25 on held-out test split.",
        dataset_version="attendance-v1",
    )

    assert meta["model_name"] == "YOLO26-Attendance-Prod"
    assert meta["version"] == "v2-finetuned"
    assert os.path.exists(meta["weights_path"])

    loaded_meta = AttendanceModelRegistry.get_production_metadata()
    assert loaded_meta is not None
    assert loaded_meta["version"] == "v2-finetuned"
    assert loaded_meta["metrics"]["count_metrics"]["mae"] == 1.25


def test_model_configuration_loading():
    """11. Verifies that attendance configuration loads correct default settings."""
    assert settings.ATTENDANCE_MODEL_FAMILY == "YOLO26"
    assert settings.ATTENDANCE_CONFIDENCE_THRESHOLD == 0.40
    assert settings.ATTENDANCE_DEVICE in ["cpu", "cuda:0", "mps"]


def test_evaluation_result_persistence(temp_registry_dir):
    """12. Verifies that stored evaluation results are loaded accurately by registry."""
    # When metadata is empty, get_production_metadata returns None
    assert AttendanceModelRegistry.get_production_metadata() is None

    # Register metadata and verify retrieval
    AttendanceModelRegistry.register_production_model(
        model_name="YOLO26",
        version="v1",
        weights_source_path=os.path.join(temp_registry_dir, "nonexistent.pt"),
        metrics={"count_metrics": {"mae": 1.5}},
        selection_rationale="Test",
    )
    retrieved = AttendanceModelRegistry.get_production_metadata()
    assert retrieved is not None
    assert retrieved["metrics"]["count_metrics"]["mae"] == 1.5


# ==============================================================================
# TESTS 13 & 14: PRODUCTION MODEL LOADING & MISSING MODEL HANDLING
# ==============================================================================

def test_production_model_loading(temp_registry_dir, monkeypatch):
    """13. Verifies loader prioritizes registered production model when present."""
    prod_weights = os.path.join(temp_registry_dir, "production", "production_model.pt")
    os.makedirs(os.path.dirname(prod_weights), exist_ok=True)
    with open(prod_weights, "wb") as f:
        f.write(b"MOCK_PT_WEIGHTS")

    AttendanceModelRegistry.register_production_model(
        model_name="YOLO26-Registered-Prod",
        version="v2-selected",
        weights_source_path=prod_weights,
        metrics={"count_metrics": {"mae": 1.2}},
        selection_rationale="Empirical validation superiority",
    )

    set_attendance_detector(None)  # Reset singleton
    detector = get_attendance_detector()

    assert detector.model_name == "YOLO26-Registered-Prod"
    assert detector.model_version == "v2-selected"
    set_attendance_detector(None)


def test_missing_model_handling(client):
    """14. Verifies evaluation API returns 'NOT_EVALUATED' when benchmark has not been run (never fake numbers)."""
    # Query /api/v1/ai/attendance/evaluation when no baseline or production JSON exists
    import backend.app.ml.attendance.registry as reg_module
    old_meta_file = reg_module.METADATA_FILE
    reg_module.METADATA_FILE = "/nonexistent/path/metadata.json"

    try:
        response = client.get("/api/v1/ai/attendance/evaluation")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["NOT_EVALUATED", "EVALUATED"]
        if data["status"] == "NOT_EVALUATED":
            assert "Evaluation results are not available yet" in data["message"]
            assert "metrics" not in data  # No fabricated metrics!
    finally:
        reg_module.METADATA_FILE = old_meta_file


def test_error_analysis_classification():
    """Verifies that failure modes (crowded occlusions, sparse false negatives) are categorized correctly."""
    evaluations = [
        ImageCountEvaluation(image_name="crowded1.jpg", actual_count=20, predicted_count=15), # Crowded undercount (-5)
        ImageCountEvaluation(image_name="crowded2.jpg", actual_count=25, predicted_count=21), # Crowded undercount (-4)
        ImageCountEvaluation(image_name="sparse1.jpg", actual_count=3, predicted_count=1),     # Sparse undercount (-2)
        ImageCountEvaluation(image_name="normal1.jpg", actual_count=10, predicted_count=10),   # Exact match
    ]
    report = AttendanceErrorAnalyzer.analyze_errors(evaluations)

    assert report["total_evaluated"] == 4
    assert report["severe_discrepancies_count"] == 2  # error > 3
    assert report["crowded_scene_failures_count"] == 2
    assert report["sparse_scene_failures_count"] == 1
    assert "UNDERCOUNTING" in report["predominant_error_type"]
