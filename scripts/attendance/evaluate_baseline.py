#!/usr/bin/env python3
"""CLI Script: Evaluate Baseline YOLO26 Attendance Presence Detector on Held-Out Test Set.

Usage:
    python scripts/attendance/evaluate_baseline.py [--dataset datasets/attendance] [--conf 0.40]
"""

import os
import sys
import argparse
import json

from backend.app.pipelines.attendance.loader import get_attendance_detector
from backend.app.ml.attendance.evaluator import AttendanceModelEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate baseline YOLO26 detector on test split.")
    parser.add_argument("--dataset", default="datasets/attendance", help="Dataset root directory")
    parser.add_argument("--split", default="test", help="Split name to evaluate on")
    parser.add_argument("--conf", type=float, default=0.40, help="Confidence threshold")
    parser.add_argument("--output", default="models/attendance/baseline/evaluation_metrics.json", help="Output JSON path")
    args = parser.parse_args()

    print(f"=== Evaluating Baseline YOLO26 Attendance Model on '{args.split}' Split ===")
    detector = get_attendance_detector()

    evaluator = AttendanceModelEvaluator(detector)
    res = evaluator.evaluate_split(
        dataset_root=args.dataset,
        split_name=args.split,
        confidence_threshold=args.conf,
    )

    if res.get("status") != "SUCCESS":
        print(f"Evaluation cannot proceed: {res.get('message', res.get('status'))}")
        print("Note: Provide real test images/annotations in datasets/attendance/test/ to evaluate.")
        sys.exit(0)

    det = res["detection_metrics"]
    cnt = res["count_metrics"]
    spd = res["speed_metrics"]

    print("\n--- Detection Metrics ---")
    print(f"Precision: {det['precision']:.4f} | Recall: {det['recall']:.4f} | mAP@50: {det['map50']:.4f}")
    print(f"True Positives: {det['true_positives']} | False Positives: {det['false_positives']} | False Negatives: {det['false_negatives']}")

    print("\n--- Headcount Metrics (SRS §FR-03 & PRD §9) ---")
    print(f"Count MAE: {cnt['mae']:.2f} people | Count RMSE: {cnt['rmse']:.2f}")
    print(f"Exact Count Match: {cnt['exact_match_pct']:.1f}%")
    print(f"Within +/- 1 Person: {cnt['within_1_pct']:.1f}%")
    print(f"Within +/- 2 People: {cnt['within_2_pct']:.1f}%")

    print(f"\nLatency: {spd['avg_inference_time_ms']:.1f} ms ({spd['fps']:.1f} FPS)")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\nSaved baseline evaluation report to {args.output}")


if __name__ == "__main__":
    main()
