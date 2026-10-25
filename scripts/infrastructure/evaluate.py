#!/usr/bin/env python3
"""CLI Script: Evaluate Infrastructure Model Weights on a Specific Dataset Split.

Usage:
    python scripts/infrastructure/evaluate.py --weights models/infrastructure/experiments/exp001/weights/best.pt --split test
"""

import os
import sys
import glob
import json
import time
import argparse
import numpy as np

from backend.app.pipelines.infrastructure.yolo26_detector import YOLO26InfrastructureDetector
from backend.app.pipelines.infrastructure.base import InfrastructureDetectionResult


def main():
    parser = argparse.ArgumentParser(description="Evaluate specific model weights on an infrastructure split.")
    parser.add_argument("--weights", required=True, help="Path to model weights (.pt)")
    parser.add_argument("--dataset", default="datasets/infrastructure", help="Dataset root directory")
    parser.add_argument("--split", default="test", help="Dataset split (val or test)")
    parser.add_argument("--conf", type=float, default=0.40, help="Confidence threshold")
    parser.add_argument("--output", default="infra_evaluation_report.json", help="Output report path")
    args = parser.parse_args()

    print(f"=== Evaluating Infrastructure Weights '{args.weights}' on '{args.split}' Split ===")
    if not os.path.exists(args.weights):
        print(f"Weights file not found: {args.weights}")
        sys.exit(1)

    img_dir = os.path.join(args.dataset, args.split, "images")
    if not os.path.exists(img_dir):
        print(f"Dataset split images not found: {img_dir}")
        sys.exit(1)

    images = sorted(glob.glob(os.path.join(img_dir, "*.jpg")) + glob.glob(os.path.join(img_dir, "*.png")))
    if not images:
        print(f"No images found in {img_dir}.")
        sys.exit(0)

    detector = YOLO26InfrastructureDetector(
        model_path=args.weights,
        model_name="YOLO26-Infrastructure",
        confidence_threshold=args.conf,
    )

    inference_times = []
    class_detected_totals = {}

    for img_p in images:
        t0 = time.perf_counter()
        res: InfrastructureDetectionResult = detector.detect(img_p, confidence_threshold=args.conf)
        t1 = time.perf_counter()
        inference_times.append((t1 - t0) * 1000.0)

        for c, count in res.class_counts.items():
            class_detected_totals[c] = class_detected_totals.get(c, 0) + count

    avg_ms = float(np.mean(inference_times)) if inference_times else 0.0
    fps = (1000.0 / avg_ms) if avg_ms > 0 else 0.0

    report = {
        "status": "EVALUATED",
        "weights": args.weights,
        "split": args.split,
        "images_evaluated": len(images),
        "confidence_threshold": args.conf,
        "speed_metrics": {
            "avg_inference_time_ms": round(avg_ms, 2),
            "fps": round(fps, 1),
        },
        "detected_totals_by_class": class_detected_totals,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved evaluation report to {args.output}")


if __name__ == "__main__":
    main()
