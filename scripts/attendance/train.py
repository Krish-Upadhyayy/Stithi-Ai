#!/usr/bin/env python3
"""CLI Script: Fine-Tune YOLO26 Attendance Presence Detection Model.

Usage:
    python scripts/attendance/train.py --exp-id attendance_yolo26_exp001 --epochs 50 --batch 16
"""

import sys
import argparse
import json
from backend.app.ml.attendance.trainer import AttendanceTrainer


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLO26 presence detector on training dataset.")
    parser.add_argument("--exp-id", default="attendance_yolo26_exp001", help="Unique experiment identifier")
    parser.add_argument("--base-weights", default="ai_models/yolo26_face_presence.pt", help="Base weights path")
    parser.add_argument("--data", default="datasets/attendance/data.yaml", help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--lr", type=float, default=0.01, help="Initial learning rate")
    parser.add_argument("--device", default="cpu", help="Device (cpu or cuda:0)")
    parser.add_argument("--workers", type=int, default=2, help="Dataloader workers")
    parser.add_argument("--notes", default="YOLO26 baseline fine-tuning experiment", help="Experiment notes")
    args = parser.parse_args()

    print(f"=== Starting YOLO26 Attendance Fine-Tuning Experiment: {args.exp_id} ===")
    trainer = AttendanceTrainer(
        base_weights=args.base_weights,
        data_yaml=args.data,
    )

    result = trainer.run_training_experiment(
        experiment_id=args.exp_id,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        lr0=args.lr,
        device=args.device,
        workers=args.workers,
        notes=args.notes,
    )

    print(f"Experiment Status: {result.get('status')}")
    if result.get("status") == "COMPLETED":
        print(f"Best weights: {result.get('best_weights_path')}")
        print(f"Last weights: {result.get('last_weights_path')}")
    elif result.get("error"):
        print(f"Notice: {result.get('error')}")


if __name__ == "__main__":
    main()
