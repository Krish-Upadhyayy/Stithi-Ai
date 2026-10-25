#!/usr/bin/env python3
"""CLI Script: Register Selected Model as the Production Attendance Model.

Usage:
    python scripts/attendance/register_model.py --name YOLO26-Face-Presence --version v2-finetuned --weights path/to/best.pt --metrics path/to/eval.json --rationale "Reduced Count MAE from 3.2 to 1.1 on held-out test split"
"""

import sys
import argparse
import json
from backend.app.ml.attendance.registry import AttendanceModelRegistry


def main():
    parser = argparse.ArgumentParser(description="Register a model as the production attendance detector.")
    parser.add_argument("--name", default="YOLO26-Face-Presence", help="Model name")
    parser.add_argument("--version", required=True, help="Model version identifier (e.g. v2-finetuned)")
    parser.add_argument("--weights", required=True, help="Path to model weights (.pt)")
    parser.add_argument("--metrics", required=True, help="Path to evaluation metrics JSON")
    parser.add_argument("--rationale", required=True, help="Reasoning for selecting this model")
    parser.add_argument("--dataset-version", default="attendance-v1", help="Dataset version identifier")
    args = parser.parse_args()

    try:
        with open(args.metrics, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)
    except Exception as e:
        print(f"Error reading metrics JSON: {e}")
        sys.exit(1)

    reg = AttendanceModelRegistry.register_production_model(
        model_name=args.name,
        version=args.version,
        weights_source_path=args.weights,
        metrics=metrics_data,
        selection_rationale=args.rationale,
        dataset_version=args.dataset_version,
    )

    print("=== Model Registered to Production Registry ===")
    print(f"Model Name: {reg['model_name']}")
    print(f"Version: {reg['version']}")
    print(f"Weights Path: {reg['weights_path']}")
    print(f"Selection Rationale: {reg['selection_rationale']}")
    print("Metadata written to models/attendance/production/model_metadata.json")


if __name__ == "__main__":
    main()
