#!/usr/bin/env python3
"""CLI Script: Validate YOLO Attendance Dataset & Check for Data Leakage.

Usage:
    python scripts/attendance/validate_dataset.py [--dataset datasets/attendance]
"""

import sys
import argparse
import json
from backend.app.ml.attendance.dataset_validator import DatasetValidator


def main():
    parser = argparse.ArgumentParser(description="Validate YOLO dataset and check for split leakage.")
    parser.add_argument("--dataset", default="datasets/attendance", help="Path to dataset root")
    args = parser.parse_args()

    print(f"=== Validating YOLO Attendance Dataset at '{args.dataset}' ===")
    validator = DatasetValidator(args.dataset)
    report = validator.validate_full_dataset()

    print("\n--- Split Summary ---")
    for split in ["train", "val", "test"]:
        s_data = report.get(split, {})
        print(f"[{split.upper()}] Images: {s_data.get('total_images', 0)} | "
              f"Annotated: {s_data.get('annotated_images', 0)} | "
              f"Empty: {s_data.get('empty_images', 0)} | "
              f"Objects: {s_data.get('total_objects', 0)} | "
              f"Avg Obj/Img: {s_data.get('avg_objects_per_image', 0.0)} | "
              f"Issues: {s_data.get('issues_count', 0)}")

    leakage = report.get("leakage_warnings", [])
    if leakage:
        print("\n--- Leakage Warnings ---")
        for w in leakage:
            print(f"! {w}")
    else:
        print("\n✓ No cross-split sequence or file leakage detected.")

    print(f"\nOverall Dataset Valid: {report.get('dataset_valid', False)}")
    
    # Save validation report
    out_file = "datasets/attendance/validation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_file}")

    if not report.get("dataset_valid", False) and any(report.get(s, {}).get("total_images", 0) > 0 for s in ["train", "val", "test"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
