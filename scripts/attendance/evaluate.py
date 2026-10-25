#!/usr/bin/env python3
"""CLI Script: Evaluate Any YOLO Attendance Model Weights on a Given Dataset Split.

Usage:
    python scripts/attendance/evaluate.py --weights models/attendance/experiments/exp001/weights/best.pt --split test
"""

import os
import sys
import argparse
import json

from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector
from backend.app.ml.attendance.evaluator import AttendanceModelEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate model weights on dataset split.")
    parser.add_argument("--weights", required=True, help="Path to model weights (.pt)")
    parser.add_argument("--dataset", default="datasets/attendance", help="Dataset root directory")
    parser.add_argument("--split", default="test", help="Dataset split (val or test)")
    parser.add_argument("--conf", type=float, default=0.40, help="Confidence threshold")
    parser.add_argument("--output", default="evaluation_report.json", help="Output JSON path")
    args = parser.parse_args()

    print(f"=== Evaluating Weights '{args.weights}' on '{args.split}' split ===")
    detector = YOLO26AttendanceDetector(
        model_path=args.weights,
        model_name="YOLO26-Attendance",
        model_version=os.path.basename(os.path.dirname(os.path.dirname(args.weights))) or "finetuned",
        confidence_threshold=args.conf,
    )

    evaluator = AttendanceModelEvaluator(detector)
    res = evaluator.evaluate_split(
        dataset_root=args.dataset,
        split_name=args.split,
        confidence_threshold=args.conf,
    )

    if res.get("status") != "SUCCESS":
        print(f"Evaluation cannot proceed: {res.get('message', res.get('status'))}")
        sys.exit(0)

    det = res["detection_metrics"]
    cnt = res["count_metrics"]
    spd = res["speed_metrics"]

    print("\n--- Detection Metrics ---")
    print(f"Precision: {det['precision']:.4f} | Recall: {det['recall']:.4f} | mAP@50: {det['map50']:.4f}")

    print("\n--- Headcount Metrics ---")
    print(f"Count MAE: {cnt['mae']:.2f} people | Count RMSE: {cnt['rmse']:.2f}")
    print(f"Exact Count Match: {cnt['exact_match_pct']:.1f}%")
    print(f"Within +/- 1 Person: {cnt['within_1_pct']:.1f}%")
    print(f"Within +/- 2 People: {cnt['within_2_pct']:.1f}%")

    print(f"\nLatency: {spd['avg_inference_time_ms']:.1f} ms ({spd['fps']:.1f} FPS)")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    main()
