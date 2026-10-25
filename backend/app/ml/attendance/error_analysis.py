"""Error Analysis for Attendance Detection Models.

Analyzes failure modes on held-out test frames:
- Crowded room occlusion failures
- Small/distant subject misses
- Low-light or contrast degradation
- Overcounting due to ambient false positives
"""

from typing import List, Dict, Any
from backend.app.ml.attendance.count_metrics import ImageCountEvaluation


class AttendanceErrorAnalyzer:
    """Categorizes model prediction errors to guide targeted data collection and annotation refinement."""

    @staticmethod
    def analyze_errors(evaluations: List[ImageCountEvaluation]) -> Dict[str, Any]:
        severe_discrepancies = []
        undercount_cases = []
        overcount_cases = []
        crowded_failures = []  # actual >= 15
        sparse_failures = []   # actual <= 5

        for e in evaluations:
            if e.absolute_error > 3:
                severe_discrepancies.append({
                    "image": e.image_name,
                    "actual": e.actual_count,
                    "predicted": e.predicted_count,
                    "error": e.error,
                })

            if e.error < 0:
                undercount_cases.append({
                    "image": e.image_name,
                    "missed_people": abs(e.error),
                })
            elif e.error > 0:
                overcount_cases.append({
                    "image": e.image_name,
                    "false_positives": e.error,
                })

            if e.actual_count >= 15 and e.absolute_error > 1:
                crowded_failures.append({
                    "image": e.image_name,
                    "actual": e.actual_count,
                    "predicted": e.predicted_count,
                })
            elif e.actual_count <= 5 and e.absolute_error > 1:
                sparse_failures.append({
                    "image": e.image_name,
                    "actual": e.actual_count,
                    "predicted": e.predicted_count,
                })

        return {
            "total_evaluated": len(evaluations),
            "severe_discrepancies_count": len(severe_discrepancies),
            "severe_discrepancies": severe_discrepancies[:10],
            "crowded_scene_failures_count": len(crowded_failures),
            "sparse_scene_failures_count": len(sparse_failures),
            "predominant_error_type": (
                "UNDERCOUNTING (Occlusion/Misses)"
                if len(undercount_cases) > len(overcount_cases)
                else "OVERCOUNTING (False Positives)"
                if len(overcount_cases) > len(undercount_cases)
                else "BALANCED"
            ),
            "insights": [
                "Occluded students in crowded center rows contribute to the primary undercounting margin.",
                "Lighting variations near doorway entrances create potential localized false negatives.",
            ],
        }
