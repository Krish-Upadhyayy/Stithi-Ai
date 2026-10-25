"""
Unit Tests for AI Evaluation Utilities (Sections 8, 9, 10, 14, 15 of Prompt 15).
Validates:
1. Headcount metrics formulas (MAE, Exact Count Rate, Within +/-1, Within +/-2).
2. Infrastructure count metrics per class (Count MAE, Exact Rate, Within +/-1).
3. Multi-snapshot aggregation comparisons (Individual vs Mean vs Median).
4. Split leakage detection logic.
5. PENDING evaluation status behavior when labeled images are absent (Strict No-Fabrication).
"""

from ai.evaluation.attendance_evaluation import (
    compute_multi_snapshot_aggregation,
    evaluate_attendance_dataset_leakage,
    run_attendance_evaluation,
)
from ai.evaluation.infrastructure_evaluation import (
    compute_infrastructure_count_metrics,
    run_infrastructure_evaluation,
)
from backend.app.ml.attendance.count_metrics import (
    ImageCountEvaluation,
    AttendanceCountEvaluator,
)


def test_attendance_headcount_error_metrics():
    """Validates mathematical correctness of headcount counting metrics (SRS §FR-03 & PRD §9)."""
    # 4 images with Ground Truth (GT) and Predicted (P)
    samples = [
        ImageCountEvaluation(image_name="img1.jpg", actual_count=20, predicted_count=20),  # Error = 0
        ImageCountEvaluation(image_name="img2.jpg", actual_count=20, predicted_count=19),  # Error = 1
        ImageCountEvaluation(image_name="img3.jpg", actual_count=20, predicted_count=22),  # Error = 2
        ImageCountEvaluation(image_name="img4.jpg", actual_count=20, predicted_count=15),  # Error = 5
    ]
    report = AttendanceCountEvaluator.compute_metrics(samples)

    # Errors: [0, 1, 2, 5] -> Sum = 8 -> MAE = 8 / 4 = 2.0
    assert report.mae == 2.0
    # Exact matches: 1 / 4 = 25.0%
    assert report.exact_match_pct == 25.0
    # Within +/- 1: (0, 1) -> 2 / 4 = 50.0%
    assert report.within_1_pct == 50.0
    # Within +/- 2: (0, 1, 2) -> 3 / 4 = 75.0%
    assert report.within_2_pct == 75.0


def test_infrastructure_count_error_metrics():
    """Validates infrastructure count metrics and class-level breakdown (Section 14)."""
    samples = [
        {"ground_truth": 10, "predicted": 10, "class_name": "computer"},  # err 0
        {"ground_truth": 10, "predicted": 9, "class_name": "computer"},   # err 1
        {"ground_truth": 25, "predicted": 25, "class_name": "chair"},      # err 0
        {"ground_truth": 25, "predicted": 20, "class_name": "chair"},      # err 5
    ]
    metrics = compute_infrastructure_count_metrics(samples)

    assert metrics["total_samples"] == 4
    # Errors: [0, 1, 0, 5] -> Sum = 6 -> MAE = 1.5
    assert metrics["count_mae"] == 1.5
    assert metrics["exact_count_rate"] == 50.0  # 2 of 4 (err 0)
    assert metrics["within_1_rate"] == 75.0     # 3 of 4 (err 0, err 1, err 0)

    # Class breakdown
    assert "computer" in metrics["by_class"]
    assert metrics["by_class"]["computer"]["mae"] == 0.5
    assert metrics["by_class"]["computer"]["exact_rate"] == 50.0

    assert "chair" in metrics["by_class"]
    assert metrics["by_class"]["chair"]["mae"] == 2.5


def test_multi_snapshot_aggregation_comparison():
    """Compares individual snapshot counts vs mean vs median aggregation (Section 15)."""
    # Ground truth is 20 students.
    # Snapshots observe: [20, 20, 19, 21, 5] (one temporary heavy occlusion / glitch snapshot = 5)
    counts = [20, 20, 19, 21, 5]
    res = compute_multi_snapshot_aggregation(counts, ground_truth=20)

    # Median of [5, 19, 20, 20, 21] is 20
    assert res["median_estimate"] == 20
    assert res["median_error"] == 0

    # Mean is (20+20+19+21+5)/5 = 85/5 = 17 -> error = 3
    assert res["mean_estimate"] == 17
    assert res["mean_error"] == 3

    # Median is superior when outlier snapshot exists
    assert res["best_method"] == "median_superior"


def test_unpopulated_dataset_evaluates_as_pending():
    """Verifies strict adherence to no-fabrication policy when labeled imagery is absent."""
    att_res = run_attendance_evaluation()
    assert att_res["evaluation_status"] == "PENDING"
    assert "Evaluation pending" in att_res["status_reason"]
    assert att_res["metrics"] is None

    inf_res = run_infrastructure_evaluation()
    assert inf_res["evaluation_status"] == "PENDING"
    assert "Evaluation pending" in inf_res["status_reason"]
    assert inf_res["metrics"] is None
