#!/usr/bin/env python3
"""CLI Script: Compare Baseline vs Fine-Tuned Infrastructure AI Models.

Usage:
    python scripts/infrastructure/compare_models.py --baseline models/infrastructure/baseline/evaluation_metrics.json --finetuned models/infrastructure/experiments/exp001/evaluation_metrics.json
"""

import sys
import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="Compare Baseline vs Fine-Tuned infrastructure models.")
    parser.add_argument("--baseline", default="models/infrastructure/baseline/evaluation_metrics.json", help="Path to baseline evaluation JSON")
    parser.add_argument("--finetuned", required=True, help="Path to fine-tuned evaluation JSON")
    parser.add_argument("--output", default="models/infrastructure/comparison_report.json", help="Output comparison JSON")
    args = parser.parse_args()

    try:
        with open(args.baseline, "r") as f:
            b_eval = json.load(f)
        with open(args.finetuned, "r") as f:
            f_eval = json.load(f)
    except Exception as e:
        print(f"Error loading evaluation files: {e}")
        sys.exit(1)

    b_spd = b_eval.get("speed_metrics", {})
    f_spd = f_eval.get("speed_metrics", {})
    b_totals = b_eval.get("detected_totals_by_class", {})
    f_totals = f_eval.get("detected_totals_by_class", {})

    print("=================================================================")
    print("    INFRASTRUCTURE MODEL COMPARISON (HELD-OUT TEST SPLIT)        ")
    print("=================================================================")
    print(f"{'METRIC':<28} | {'BASELINE':<12} | {'FINE-TUNED':<12}")
    print("-----------------------------------------------------------------")
    print(f"{'Avg Latency (ms)':<28} | {b_spd.get('avg_inference_time_ms', '—'):<12} | {f_spd.get('avg_inference_time_ms', '—'):<12}")
    print(f"{'Throughput (FPS)':<28} | {b_spd.get('fps', '—'):<12} | {f_spd.get('fps', '—'):<12}")

    all_classes = sorted(set(b_totals.keys()).union(set(f_totals.keys())))
    print("-----------------------------------------------------------------")
    print("Class-wise Detections (Total Detected Assets):")
    for cls_name in all_classes:
        b_cnt = b_totals.get(cls_name, 0)
        f_cnt = f_totals.get(cls_name, 0)
        print(f"{cls_name:<28} | {b_cnt:<12} | {f_cnt:<12}")
    print("=================================================================")

    comparison = {
        "baseline": b_eval,
        "finetuned": f_eval,
        "class_comparison": {
            cls_name: {
                "baseline": b_totals.get(cls_name, 0),
                "finetuned": f_totals.get(cls_name, 0),
            }
            for cls_name in all_classes
        },
    }

    with open(args.output, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\nSaved comparison report to {args.output}")


if __name__ == "__main__":
    main()
