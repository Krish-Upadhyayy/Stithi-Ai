#!/usr/bin/env python3
"""CLI Script: Evaluate and Calibrate Confidence Thresholds on Validation Data.

Usage:
    python scripts/attendance/tune_threshold.py [--weights path/to/weights.pt] [--dataset datasets/attendance]
"""

import sys
import argparse
import json
from backend.app.pipelines.attendance.loader import get_attendance_detector
from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector
from backend.app.ml.attendance.evaluator import AttendanceModelEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate confidence thresholds on validation set.")
    parser.add_argument("--weights", default=None, help="Optional weights path. Defaults to configured detector.")
    parser.add_argument("--dataset", default="datasets/attendance", help="Dataset root directory")
    parser.add_argument("--split", default="val", help="Split to calibrate on (must be val, NEVER test)")
    args = parser.parse_args()

    if args.weights:
        detector = YOLO26AttendanceDetector(model_path=args.weights)
    else:
        detector = get_attendance_detector()

    evaluator = AttendanceModelEvaluator(detector)
    thresholds = [0.25, 0.35, 0.45, 0.55, 0.65]

    print(f"=== Calibrating Confidence Threshold on '{args.split}' Split ===")
    print(f"{'THRESHOLD':<10} | {'PRECISION':<10} | {'RECALL':<10} | {'COUNT MAE':<10} | {'EXACT MATCH %':<15}")
    print("----------------------------------------------------------------------")

    results = []
    best_conf = 0.40
    best_mae = 999.0

    for conf in thresholds:
        res = evaluator.evaluate_split(args.dataset, split_name=args.split, confidence_threshold=conf)
        if res.get("status") != "SUCCESS":
            print(f"Could not calibrate: {res.get('message')}")
            sys.exit(0)

        p = res["detection_metrics"]["precision"]
        r = res["detection_metrics"]["recall"]
        mae = res["count_metrics"]["mae"]
        exact = res["count_metrics"]["exact_match_pct"]

        print(f"{conf:<10.2f} | {p:<10.4f} | {r:<10.4f} | {mae:<10.2f} | {exact:<15.1f}")
        results.append({"conf": conf, "precision": p, "recall": r, "mae": mae, "exact": exact})

        if mae < best_mae:
            best_mae = mae
            best_conf = conf

    print("----------------------------------------------------------------------")
    print(f"Recommended Calibration: conf={best_conf:.2f} (Yields lowest validation Count MAE = {best_mae:.2f})")

    out_file = "models/attendance/threshold_calibration.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"calibrations": results, "recommended_threshold": best_conf}, f, indent=2)
    print(f"Saved threshold calibration analysis to {out_file}")


if __name__ == "__main__":
    main()
