"""Attendance Count Evaluation Metrics.

Computes headcount-specific metrics per SRS §FR-03 & PRD §9:
- Count MAE (Mean Absolute Error)
- Count RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error)
- Exact headcount match percentage
- Accuracy within +/-1 person tolerance
- Accuracy within +/-2 people tolerance
- Overcount vs Undercount bias analysis
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ImageCountEvaluation:
    image_name: str
    actual_count: int
    predicted_count: int
    absolute_error: int = field(init=False)
    error: int = field(init=False)

    def __post_init__(self):
        self.error = self.predicted_count - self.actual_count
        self.absolute_error = abs(self.error)


@dataclass
class AttendanceCountMetricsReport:
    total_images: int = 0
    total_actual_people: int = 0
    total_predicted_people: int = 0
    mae: float = 0.0
    rmse: float = 0.0
    mape: Optional[float] = None
    exact_match_pct: float = 0.0
    within_1_pct: float = 0.0
    within_2_pct: float = 0.0
    overcount_count: int = 0
    undercount_count: int = 0
    exact_count: int = 0
    sample_evaluations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_images": self.total_images,
            "total_actual_people": self.total_actual_people,
            "total_predicted_people": self.total_predicted_people,
            "mae": round(self.mae, 2),
            "rmse": round(self.rmse, 2),
            "mape": round(self.mape, 2) if self.mape is not None else None,
            "exact_match_pct": round(self.exact_match_pct, 1),
            "within_1_pct": round(self.within_1_pct, 1),
            "within_2_pct": round(self.within_2_pct, 1),
            "bias_analysis": {
                "overcounts": self.overcount_count,
                "undercounts": self.undercount_count,
                "exact": self.exact_count,
            },
            "sample_evaluations": self.sample_evaluations,
        }


class AttendanceCountEvaluator:
    """Evaluates attendance headcount estimation accuracy against ground truth annotations."""

    @staticmethod
    def compute_metrics(evaluations: List[ImageCountEvaluation]) -> AttendanceCountMetricsReport:
        """Computes comprehensive count metrics from a list of per-image actual vs predicted counts."""
        if not evaluations:
            return AttendanceCountMetricsReport()

        n = len(evaluations)
        abs_errors = [e.absolute_error for e in evaluations]
        sq_errors = [e.absolute_error ** 2 for e in evaluations]

        total_actual = sum(e.actual_count for e in evaluations)
        total_pred = sum(e.predicted_count for e in evaluations)

        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(sq_errors) / n)

        # MAPE calculation (skip images where actual_count is 0 to avoid division by zero)
        non_zero_actual = [e for e in evaluations if e.actual_count > 0]
        if non_zero_actual:
            mape = sum(abs(e.predicted_count - e.actual_count) / e.actual_count for e in non_zero_actual) / len(non_zero_actual) * 100.0
        else:
            mape = None

        exact_count = sum(1 for e in evaluations if e.absolute_error == 0)
        within_1 = sum(1 for e in evaluations if e.absolute_error <= 1)
        within_2 = sum(1 for e in evaluations if e.absolute_error <= 2)

        overcount_count = sum(1 for e in evaluations if e.error > 0)
        undercount_count = sum(1 for e in evaluations if e.error < 0)

        exact_match_pct = (exact_count / n) * 100.0
        within_1_pct = (within_1 / n) * 100.0
        within_2_pct = (within_2 / n) * 100.0

        sample_evals = [
            {
                "image": e.image_name,
                "actual": e.actual_count,
                "predicted": e.predicted_count,
                "abs_error": e.absolute_error,
            }
            for e in evaluations[:20]  # Store up to first 20 for inspection
        ]

        return AttendanceCountMetricsReport(
            total_images=n,
            total_actual_people=total_actual,
            total_predicted_people=total_pred,
            mae=mae,
            rmse=rmse,
            mape=mape,
            exact_match_pct=exact_match_pct,
            within_1_pct=within_1_pct,
            within_2_pct=within_2_pct,
            overcount_count=overcount_count,
            undercount_count=undercount_count,
            exact_count=exact_count,
            sample_evaluations=sample_evals,
        )
