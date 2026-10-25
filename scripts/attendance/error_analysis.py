#!/usr/bin/env python3
"""CLI Script: Attendance Error Analysis & Visual Verification.

Categorizes model failure modes:
- Crowded room occlusions (dense seating)
- Small / distant subjects
- False positives on classroom objects / furniture
- Severe discrepancy breakdowns
- Generates visual overlays with Ground Truth (Green) and Predictions (Cyan)

Usage:
    python scripts/attendance/error_analysis.py [--dataset datasets/attendance] [--split test] [--visualize]
"""

import os
import sys
import argparse
import json
from typing import List

from backend.app.pipelines.attendance.loader import get_attendance_detector
from backend.app.ml.attendance.count_metrics import ImageCountEvaluation
from backend.app.ml.attendance.error_analysis import AttendanceErrorAnalyzer
from backend.app.ml.attendance.visualizer import EvaluationVisualizer


def main():
    parser = argparse.ArgumentParser(description="Run failure mode and error analysis on attendance predictions.")
    parser.add_argument("--dataset", default="datasets/attendance", help="Dataset root directory")
    parser.add_argument("--split", default="test", help="Split name to analyze")
    parser.add_argument("--eval-json", default="models/attendance/baseline/evaluation_metrics.json", help="Path to evaluation JSON")
    parser.add_argument("--visualize", action="store_true", help="Generate side-by-side / overlay bounding box images")
    parser.add_argument("--output-dir", default="storage/evidence/eval_visualizations", help="Visualization output dir")
    parser.add_argument("--report-out", default="models/attendance/error_analysis_report.json", help="Error report JSON output path")
    args = parser.parse_args()

    evaluations: List[ImageCountEvaluation] = []

    if os.path.exists(args.eval_json):
        with open(args.eval_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("count_metrics", {}).get("sample_evaluations", [])
        for s in samples:
            evaluations.append(
                ImageCountEvaluation(
                    image_name=s.get("image", "unknown"),
                    actual_count=int(s.get("actual", 0)),
                    predicted_count=int(s.get("predicted", 0)),
                )
            )

    if not evaluations:
        print(f"No evaluations found in {args.eval_json}. Please run evaluate_baseline.py or evaluate.py first.")
        sys.exit(0)

    print(f"=== Running Attendance Detection Error Analysis ({len(evaluations)} samples) ===")
    analysis = AttendanceErrorAnalyzer.analyze_errors(evaluations)

    print(f"Predominant Error Tendency  : {analysis.get('predominant_error_type')}")
    print(f"Severe Discrepancies (>3)   : {analysis.get('severe_discrepancies_count')}")
    print(f"Crowded Scene Failures      : {analysis.get('crowded_scene_failures_count')}")
    print(f"Sparse Scene Failures       : {analysis.get('sparse_scene_failures_count')}")

    print("\nCategorized Insights:")
    for ins in analysis.get("insights", []):
        print(f"  • {ins}")

    if args.visualize:
        print(f"\nGenerating visual evaluation overlays in '{args.output_dir}'...")
        os.makedirs(args.output_dir, exist_ok=True)
        img_dir = os.path.join(args.dataset, args.split, "images")
        lbl_dir = os.path.join(args.dataset, args.split, "labels")

        detector = get_attendance_detector()
        rendered_count = 0

        for e in evaluations[:10]:
            img_path = os.path.join(img_dir, e.image_name)
            if not os.path.exists(img_path):
                continue

            base = os.path.splitext(e.image_name)[0]
            lbl_path = os.path.join(lbl_dir, f"{base}.txt")

            gt_boxes = []
            if os.path.exists(lbl_path):
                with open(lbl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            xc, yc, w, h = map(float, parts[1:])
                            gt_boxes.append([xc - w/2, yc - h/2, xc + w/2, yc + h/2])

            res = detector.detect(img_path)
            pred_boxes = [d.bbox for d in res.detections]

            out_file = f"overlay_{base}.jpg"
            out_p = EvaluationVisualizer.render_overlay(
                image_path=img_path,
                gt_boxes_xyxy=gt_boxes,
                pred_boxes_xyxy=pred_boxes,
                output_dir=args.output_dir,
                output_filename=out_file,
            )
            if out_p:
                rendered_count += 1

        print(f"Generated {rendered_count} visual evaluation overlays.")

    os.makedirs(os.path.dirname(os.path.abspath(args.report_out)), exist_ok=True)
    with open(args.report_out, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"\nSaved failure mode report to {args.report_out}")


if __name__ == "__main__":
    main()
