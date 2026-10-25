"""Compliance Engine foundation.

Calculates discrepancy between physical attendance and aggregate AI observations.
Calculates discrepancy between sanctioned Excel inventory and observed assets.
"""

from typing import List, Dict, Any, Optional
import statistics


class ComplianceEngine:
    """Core comparator for attendance and infrastructure compliance."""

    def __init__(self, attendance_tolerance: int = 2):
        self.attendance_tolerance = attendance_tolerance

    def aggregate_attendance_observations(self, counts: List[int], method: str = "median") -> int:
        """Aggregates multiple snapshot observations (e.g. median)."""
        if not counts:
            return 0
        if method == "median":
            return int(statistics.median(counts))
        return int(sum(counts) / len(counts))

    def evaluate_attendance(
        self,
        physical_attendance: int,
        observed_attendance: int,
        tolerance: Optional[int] = None
    ) -> Dict[str, Any]:
        """Compares physical attendance vs observed attendance."""
        effective_tolerance = tolerance if tolerance is not None else self.attendance_tolerance
        difference = physical_attendance - observed_attendance
        is_discrepant = abs(difference) > effective_tolerance

        return {
            "physical_attendance": physical_attendance,
            "observed_attendance": observed_attendance,
            "difference": difference,
            "tolerance": effective_tolerance,
            "is_discrepancy": is_discrepant,
            "status": "NON_COMPLIANT" if is_discrepant else "COMPLIANT"
        }

    def evaluate_infrastructure(
        self,
        required_quantity: int,
        detected_quantity: int
    ) -> Dict[str, Any]:
        """Compares required quantity from Excel against detected quantity."""
        difference = required_quantity - detected_quantity
        is_discrepant = difference > 0

        return {
            "required_quantity": required_quantity,
            "detected_quantity": detected_quantity,
            "difference": difference,
            "is_discrepancy": is_discrepant,
            "status": "DISCREPANCY_DETECTED" if is_discrepant else "COMPLIANT"
        }
