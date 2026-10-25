#!/usr/bin/env python3
"""CLI Script: Fine-Tune YOLO26 Infrastructure Detection Model.

Usage:
    python scripts/infrastructure/train.py --exp-id infra_yolo26_exp001 --epochs 50 --batch 16
"""

import os
import sys
import argparse
import json
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLO26 infrastructure asset detector.")
    parser.add_argument("--exp-id", default="infra_yolo26_exp001", help="Unique experiment identifier")
    parser.add_argument("--base-weights", default="ai_models/yolo26_infrastructure.pt", help="Base weights path")
    parser.add_argument("--data", default="datasets/infrastructure/data.yaml", help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--lr", type=float, default=0.01, help="Initial learning rate")
    parser.add_argument("--device", default="cpu", help="Device (cpu, cuda:0, mps)")
    parser.add_argument("--workers", type=int, default=2, help="Dataloader workers")
    parser.add_argument("--notes", default="YOLO26 infrastructure baseline fine-tuning experiment", help="Notes")
    args = parser.parse_args()

    print(f"=== Starting YOLO26 Infrastructure Training Experiment: {args.exp_id} ===")
    exp_dir = os.path.join("models/infrastructure/experiments", args.exp_id)
    os.makedirs(exp_dir, exist_ok=True)

    record = {
        "experiment_id": args.exp_id,
        "base_weights": args.base_weights,
        "data_yaml": args.data,
        "hyperparameters": {
            "epochs": args.epochs,
            "batch_size": args.batch,
            "imgsz": args.imgsz,
            "lr": args.lr,
            "device": args.device,
            "workers": args.workers,
        },
        "created_at": datetime.utcnow().isoformat(),
        "notes": args.notes,
        "status": "INITIALIZED",
    }

    if not os.path.exists(args.data):
        print(f"Dataset config not found at: {args.data}")
        record["status"] = "DATASET_NOT_FOUND"
        with open(os.path.join(exp_dir, "experiment_metadata.json"), "w") as f:
            json.dump(record, f, indent=2)
        sys.exit(0)

    try:
        from ultralytics import YOLO
        weights_to_load = args.base_weights if os.path.exists(args.base_weights) else "yolo26n.pt"
        print(f"Loading weights {weights_to_load}...")
        model = YOLO(weights_to_load)

        results = model.train(
            data=args.data,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            lr0=args.lr,
            device=args.device,
            workers=args.workers,
            project="models/infrastructure/experiments",
            name=args.exp_id,
            exist_ok=True,
            verbose=False,
        )

        record["status"] = "COMPLETED"
        record["best_weights_path"] = os.path.join(exp_dir, "weights", "best.pt")
        print(f"Training completed. Best weights saved to: {record['best_weights_path']}")
    except Exception as e:
        print(f"Training halted or simulated: {e}")
        record["status"] = "EXECUTION_HALTED"
        record["error"] = str(e)

    with open(os.path.join(exp_dir, "experiment_metadata.json"), "w") as f:
        json.dump(record, f, indent=2)


if __name__ == "__main__":
    main()
