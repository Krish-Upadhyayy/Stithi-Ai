#!/usr/bin/env python3
"""CLI Script: Evaluate Baseline YOLO26 Infrastructure Model on Held-Out Test Split.

Usage:
    python scripts/infrastructure/evaluate_baseline.py [--dataset datasets/infrastructure] [--split test]
"""

import os
import sys
import glob
import json
import time
import argparse
import numpy as np

from backend.app.pipelines.infrastructure.loader import get_infrastructure_detector
from backend.app.pipelines.infrastructure.base import InfrastructureDetectionResult


def main():
    parser = argparse.ArgumentParser(description="Evaluate baseline YOLO26 infrastructure model on test split.")
    parser.add_argument("--dataset", default="datasets/infrastructure", help="Dataset root directory")
    parser.add_argument("--split", default="test", help="Split name to evaluate on")
    parser.add_argument("--conf", type=float, default=0.40, help="Confidence threshold")
    parser.add_argument("--output", default="models/infrastructure/baseline/evaluation_metrics.json", help="Output JSON path")
    args = parser.parse_args()

    print(f"=== Evaluating Baseline YOLO26 Infrastructure Model on '{args.split}' Split ===")
    detector = get_infrastructure_detector()

    if not detector.is_available():
        print(f"Notice: Infrastructure model weights are not configured at '{detector.model_path}'.")
        print("To run empirical evaluation, place trained YOLO26 weights at that location.")
        sys.exit(0)

    img_dir = os.path.join(args.dataset, args.split, "images")
    if not os.path.exists(img_dir):
        print(f"Dataset directory not found: {img_dir}")
        sys.exit(0)

    images = sorted(glob.glob(os.path.join(img_dir, "*.jpg")) + glob.glob(os.path.join(img_dir, "*.png")))
    if not images:
        print(f"No test images found in {img_dir}. Ingest test images to run baseline evaluation.")
        sys.exit(0)

    total_images = len(images)
    inference_times = []
    class_detected_totals = {}

    print(f"Evaluating {total_images} frames with conf_threshold={args.conf}...")

    for img_path in images:
        t0 = time.perf_counter()
        res: InfrastructureDetectionResult = detector.detect(img_path, confidence_threshold=args.conf)
        t1 = time.perf_counter()
        inference_times.append((t1 - t0) * 1000.0)

        for c, count in res.class_counts.items():
            class_detected_totals[c] = class_detected_totals.get(c, 0) + count

    avg_ms = float(np.mean(inference_times)) if inference_times else 0.0
    fps = (1000.0 / avg_ms) if avg_ms > 0 else 0.0

    eval_report = {
        "status": "EVALUATED",
        "model_name": detector.model_name,
        "model_version": detector.model_version,
        "split": args.split,
        "images_evaluated": total_images,
        "confidence_threshold": args.conf,
        "speed_metrics": {
            "avg_inference_time_ms": round(avg_ms, 2),
            "fps": round(fps, 1),
        },
        "detected_totals_by_class": class_detected_totals,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    print("\n--- Evaluation Summary ---")
    print(f"Images Evaluated : {total_images}")
    print(f"Average Latency  : {avg_ms:.2f} ms ({fps:.1f} FPS)")
    print(f"Detected Totals  : {class_detected_totals}")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)
    print(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()
