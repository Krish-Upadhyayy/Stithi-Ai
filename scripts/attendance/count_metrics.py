#!/usr/bin/env python3
"""CLI Script: Compute Attendance Headcount Metrics.

Performs standalone headcount error calculations per SRS §FR-03 & PRD §9:
- Count MAE (Mean Absolute Error)
- Count RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error, handles actual=0)
- Exact Match %
- Within +/- 1 Person %
- Within +/- 2 People %
- Overcount vs Undercount Bias Breakdown

Usage:
    python scripts/attendance/count_metrics.py --eval-json models/attendance/baseline/evaluation_metrics.json
    python scripts/attendance/count_metrics.py --input-csv path/to/counts.csv
"""

import sys
import argparse
import json
import csv
import os
from typing import List

from backend.app.ml.attendance.count_metrics import (
    ImageCountEvaluation,
    AttendanceCountEvaluator,
    AttendanceCountMetricsReport,
)


def load_from_eval_json(file_path: str) -> List[ImageCountEvaluation]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = data.get("count_metrics", {}).get("sample_evaluations", [])
    evaluations = []
    for s in samples:
        evaluations.append(
            ImageCountEvaluation(
                image_name=s.get("image", "unknown"),
                actual_count=int(s.get("actual", 0)),
                predicted_count=int(s.get("predicted", 0)),
            )
        )
    return evaluations


def load_from_csv(file_path: str) -> List[ImageCountEvaluation]:
    evaluations = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            evaluations.append(
                ImageCountEvaluation(
                    image_name=row.get("image", row.get("image_name", "unknown")),
                    actual_count=int(row.get("actual", row.get("actual_count", 0))),
                    predicted_count=int(row.get("predicted", row.get("predicted_count", 0))),
                )
            )
    return evaluations


def main():
    parser = argparse.ArgumentParser(description="Compute attendance headcount evaluation metrics.")
    parser.add_argument("--eval-json", help="Path to evaluation report JSON containing sample evaluations")
    parser.add_argument("--input-csv", help="Path to CSV file with 'image', 'actual', 'predicted' columns")
    parser.add_argument("--output", help="Optional path to save metrics JSON")
    args = parser.parse_args()

    evaluations: List[ImageCountEvaluation] = []

    if args.eval_json:
        if not os.path.exists(args.eval_json):
            print(f"Error: File not found: {args.eval_json}")
            sys.exit(1)
        evaluations = load_from_eval_json(args.eval_json)
    elif args.input_csv:
        if not os.path.exists(args.input_csv):
            print(f"Error: File not found: {args.input_csv}")
            sys.exit(1)
        evaluations = load_from_csv(args.input_csv)
    else:
        # Check if default baseline eval exists
        default_baseline = "models/attendance/baseline/evaluation_metrics.json"
        if os.path.exists(default_baseline):
            print(f"Loading default baseline evaluation report: {default_baseline}")
            evaluations = load_from_eval_json(default_baseline)
        else:
            print("Please specify --eval-json or --input-csv.")
            parser.print_help()
            sys.exit(1)

    if not evaluations:
        print("No evaluation records found.")
        sys.exit(0)

    report: AttendanceCountMetricsReport = AttendanceCountEvaluator.compute_metrics(evaluations)
    res = report.to_dict()

    print("\n=======================================================")
    print("         ATTENDANCE HEADCOUNT EVALUATION METRICS       ")
    print("=======================================================")
    print(f"Total Images Evaluated     : {res['total_images']}")
    print(f"Total Actual Attendees     : {res['total_actual_people']}")
    print(f"Total Predicted Attendees  : {res['total_predicted_people']}")
    print(f"Count MAE (Mean Abs Error) : {res['mae']:.2f} people")
    print(f"Count RMSE                 : {res['rmse']:.2f}")
    if res['mape'] is not None:
        print(f"MAPE                       : {res['mape']:.2f}%")
    else:
        print("MAPE                       : N/A (all actual counts were 0)")
    print(f"Exact Count Match Rate     : {res['exact_match_pct']:.1f}%")
    print(f"Accuracy within +/- 1 person: {res['within_1_pct']:.1f}%")
    print(f"Accuracy within +/- 2 people: {res['within_2_pct']:.1f}%")
    print("-------------------------------------------------------")
    print(f"Overcounts (+): {res['bias_analysis']['overcounts']} | "
          f"Undercounts (-): {res['bias_analysis']['undercounts']} | "
          f"Exact (=): {res['bias_analysis']['exact']}")
    print("=======================================================\n")

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"Saved headcount metrics to {args.output}")


if __name__ == "__main__":
    main()
