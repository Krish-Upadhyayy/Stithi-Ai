"""
AI Attendance Evaluation Module (YOLO26)
Computes empirical metrics when dataset is present; strictly flags PENDING when unavailable.
Zero synthetic numbers or fabricated accuracies.
"""

import os
import json
from typing import Dict, Any, List, Optional
import numpy as np

from backend.app.ml.attendance.count_metrics import (
    ImageCountEvaluation,
    AttendanceCountEvaluator,
    AttendanceCountMetricsReport,
)
from backend.app.ml.attendance.dataset_validator import DatasetValidator


def evaluate_attendance_dataset_leakage(dataset_root: str = "datasets/attendance") -> Dict[str, Any]:
    """
    Checks train/val/test splits for data leakage (e.g., frames from same video in multiple splits).
    """
    validator = DatasetValidator(dataset_root)
    report = validator.validate_full_dataset()
    return {
        "dataset_root": dataset_root,
        "leakage_warnings": report.get("leakage_warnings", []),
        "split_summary": {
            s: report.get(s, {}).get("total_images", 0) for s in ["train", "val", "test"]
        },
        "leakage_free": len(report.get("leakage_warnings", [])) == 0,
    }


def compute_multi_snapshot_aggregation(
    snapshot_counts: List[int],
    ground_truth: int,
) -> Dict[str, Any]:
    """
    Compares individual snapshot counts vs mean aggregation vs median aggregation.
    Per Section 15 of Prompt 15:
    - individual snapshot count
    - mean aggregation
    - median aggregation
    """
    if not snapshot_counts:
        return {
            "status": "NO_SNAPSHOTS",
            "ground_truth": ground_truth,
            "individual_counts": [],
            "mean_estimate": None,
            "median_estimate": None,
            "individual_mae": None,
            "mean_error": None,
            "median_error": None,
        }

    mean_val = float(np.mean(snapshot_counts))
    median_val = float(np.median(snapshot_counts))
    rounded_mean = int(round(mean_val))
    rounded_median = int(round(median_val))

    individual_errors = [abs(c - ground_truth) for c in snapshot_counts]
    individual_mae = float(np.mean(individual_errors))
    mean_error = abs(rounded_mean - ground_truth)
    median_error = abs(rounded_median - ground_truth)

    best_method = "inconclusive"
    if median_error < mean_error:
        best_method = "median_superior"
    elif mean_error < median_error:
        best_method = "mean_superior"
    else:
        best_method = "tied"

    return {
        "ground_truth": ground_truth,
        "individual_counts": snapshot_counts,
        "individual_mae": individual_mae,
        "mean_estimate": rounded_mean,
        "mean_exact": mean_val,
        "mean_error": mean_error,
        "median_estimate": rounded_median,
        "median_exact": median_val,
        "median_error": median_error,
        "best_method": best_method,
    }


def run_attendance_evaluation(
    dataset_root: str = "datasets/attendance",
    weights_path: Optional[str] = None,
    thresholds: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Evaluates YOLO26 attendance detector.
    If real labeled dataset is absent, returns PENDING without fabricated metrics.
    """
    if thresholds is None:
        thresholds = [0.25, 0.30, 0.40, 0.50, 0.60]

    import glob
    test_images_dir = os.path.join(dataset_root, "test", "images")
    image_files = []
    if os.path.exists(test_images_dir):
        image_files = (
            glob.glob(os.path.join(test_images_dir, "*.jpg"))
            + glob.glob(os.path.join(test_images_dir, "*.jpeg"))
            + glob.glob(os.path.join(test_images_dir, "*.png"))
        )
    has_test_data = len(image_files) > 0

    leakage_check = evaluate_attendance_dataset_leakage(dataset_root)

    if not has_test_data:
        return {
            "pipeline": "YOLO26-Attendance",
            "evaluation_status": "PENDING",
            "status_reason": "Evaluation pending because a validated labeled dataset is not currently available.",
            "dataset_root": dataset_root,
            "evaluated_splits": {
                "train_images": leakage_check["split_summary"].get("train", 0),
                "val_images": leakage_check["split_summary"].get("val", 0),
                "test_images": leakage_check["split_summary"].get("test", 0),
            },
            "leakage_check": leakage_check,
            "metrics": None,
            "threshold_experiments": None,
            "notes": "Adheres to SIH strict no-fabrication policy. Accuracy and MAE require ground-truth labeled imagery.",
        }

    # If test data exists, execute real evaluation using AttendanceModelEvaluator
    from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector
    from backend.app.ml.attendance.evaluator import AttendanceModelEvaluator

    weights = weights_path or "models/attendance/baseline/yolov8n.pt"
    detector = YOLO26AttendanceDetector(model_path=weights)
    evaluator = AttendanceModelEvaluator(detector)

    threshold_results = {}
    for conf in thresholds:
        res = evaluator.evaluate_split(
            dataset_root=dataset_root,
            split_name="test",
            confidence_threshold=conf,
        )
        threshold_results[f"conf_{conf:.2f}"] = res

    best_conf = 0.40
    primary_eval = threshold_results.get(f"conf_{best_conf:.2f}", {})

    return {
        "pipeline": "YOLO26-Attendance",
        "evaluation_status": "COMPLETED",
        "dataset_root": dataset_root,
        "weights_evaluated": weights,
        "leakage_check": leakage_check,
        "primary_threshold": best_conf,
        "detection_metrics": primary_eval.get("detection_metrics"),
        "count_metrics": primary_eval.get("count_metrics"),
        "speed_metrics": primary_eval.get("speed_metrics"),
        "threshold_experiments": threshold_results,
    }
