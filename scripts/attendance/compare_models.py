#!/usr/bin/env python3
"""CLI Script: Compare Baseline vs Fine-Tuned Attendance Detection Models.

Usage:
    python scripts/attendance/compare_models.py --baseline models/attendance/baseline/evaluation_metrics.json --finetuned models/attendance/experiments/exp001/evaluation_metrics.json
"""

import sys
import argparse
import json
from backend.app.ml.attendance.registry import AttendanceModelRegistry


def main():
    parser = argparse.ArgumentParser(description="Compare Baseline vs Fine-Tuned evaluation reports.")
    parser.add_argument("--baseline", default="models/attendance/baseline/evaluation_metrics.json", help="Path to baseline evaluation JSON")
    parser.add_argument("--finetuned", required=True, help="Path to fine-tuned evaluation JSON")
    parser.add_argument("--output", default="models/attendance/comparison_report.json", help="Output comparison JSON path")
    args = parser.parse_args()

    try:
        with open(args.baseline, "r", encoding="utf-8") as f:
            b_eval = json.load(f)
        with open(args.finetuned, "r", encoding="utf-8") as f:
            f_eval = json.load(f)
    except Exception as e:
        print(f"Error reading evaluation reports: {e}")
        sys.exit(1)

    comp = AttendanceModelRegistry.compare_models(b_eval, f_eval)

    print("=================================================================")
    print("      BASELINE VS FINE-TUNED MODEL COMPARISON (HELD-OUT TEST)     ")
    print("=================================================================")
    print(f"{'METRIC':<25} | {'BASELINE':<12} | {'FINE-TUNED':<12} | {'DELTA':<10}")
    print("-----------------------------------------------------------------")

    metrics = comp["metrics_comparison"]
    for k, v in metrics.items():
        b_val = str(v.get("baseline", "—"))
        f_val = str(v.get("finetuned", "—"))
        d_val = f"{v.get('delta', '—'):+}" if v.get("delta") is not None else "—"
        print(f"{k:<25} | {b_val:<12} | {f_val:<12} | {d_val:<10}")

    print("-----------------------------------------------------------------")
    print(f"Selection Insight: {comp['recommendation']}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(comp, f, indent=2)
    print(f"\nSaved comparison analysis to {args.output}")


if __name__ == "__main__":
    main()
