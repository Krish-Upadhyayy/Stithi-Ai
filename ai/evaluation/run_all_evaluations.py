#!/usr/bin/env python3
"""
Unified AI Evaluation Runner
Executes actual evaluation runs if labeled datasets are present.
Outputs structured JSON and logs status cleanly as PENDING if data is missing.
"""

import sys
import os
import json
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.evaluation.attendance_evaluation import run_attendance_evaluation
from ai.evaluation.infrastructure_evaluation import run_infrastructure_evaluation


def main():
    print("===================================================================")
    print("      SIH AI MODEL EVALUATION RUNNER (YOLO26 PIPELINES)           ")
    print("===================================================================")

    print("\n[1/2] Evaluating YOLO26 Attendance Pipeline...")
    att_results = run_attendance_evaluation()
    print(f"Status: {att_results['evaluation_status']}")
    if att_results['evaluation_status'] == "PENDING":
        print(f"Reason: {att_results['status_reason']}")
    else:
        print("Detection metrics computed successfully.")

    print("\n[2/2] Evaluating YOLO26 Infrastructure Pipeline...")
    inf_results = run_infrastructure_evaluation()
    print(f"Status: {inf_results['evaluation_status']}")
    if inf_results['evaluation_status'] == "PENDING":
        print(f"Reason: {inf_results['status_reason']}")
    else:
        print("Infrastructure metrics computed successfully.")

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "attendance_evaluation": att_results,
        "infrastructure_evaluation": inf_results,
    }

    out_path = os.path.join(PROJECT_ROOT, "docs", "ai_evaluation_status.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nConsolidated status written to: {out_path}")
    print("===================================================================")


if __name__ == "__main__":
    main()
