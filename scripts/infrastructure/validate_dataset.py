#!/usr/bin/env python3
"""CLI Script: Validate YOLO Infrastructure Dataset & Check Integrity.

Checks:
- Missing images vs missing labels
- Malformed YOLO coordinate tuples
- Coordinate bounds [0.0, 1.0]
- Degenerate zero-size bounding boxes
- Allowed class IDs (0..4 for chair, computer, projector, sewing machine, workbench)
- Split leakage across train, val, test
- Generates empirical validation summary (zero fabricated numbers)

Usage:
    python scripts/infrastructure/validate_dataset.py [--dataset datasets/infrastructure]
"""

import os
import sys
import glob
import json
import argparse
from typing import Dict, List, Any, Set
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_CLASSES = {0, 1, 2, 3, 4}
CLASS_NAMES = {
    0: "chair",
    1: "computer",
    2: "projector",
    3: "sewing machine",
    4: "workbench",
}


def validate_split(dataset_root: str, split_name: str) -> Dict[str, Any]:
    split_dir = os.path.join(dataset_root, split_name)
    img_dir = os.path.join(split_dir, "images")
    lbl_dir = os.path.join(split_dir, "labels")

    report: Dict[str, Any] = {
        "split": split_name,
        "total_images": 0,
        "annotated_images": 0,
        "empty_images": 0,
        "missing_labels": 0,
        "corrupt_images": 0,
        "total_objects": 0,
        "class_distribution": {name: 0 for name in CLASS_NAMES.values()},
        "issues": [],
        "is_valid": True,
    }

    if not os.path.exists(img_dir):
        report["is_valid"] = False
        report["error"] = f"Directory not found: {img_dir}"
        return report

    image_files = []
    for ext in IMAGE_EXTS:
        image_files.extend(glob.glob(os.path.join(img_dir, f"*{ext}")))
        image_files.extend(glob.glob(os.path.join(img_dir, f"*{ext.upper()}")))

    report["total_images"] = len(image_files)

    for img_p in image_files:
        try:
            with Image.open(img_p) as im:
                im.verify()
        except Exception:
            report["corrupt_images"] += 1
            report["issues"].append(f"Corrupt image file: {os.path.basename(img_p)}")
            report["is_valid"] = False
            continue

        base_name = os.path.splitext(os.path.basename(img_p))[0]
        lbl_p = os.path.join(lbl_dir, f"{base_name}.txt")

        if not os.path.exists(lbl_p):
            report["missing_labels"] += 1
            report["issues"].append(f"Missing label file for: {os.path.basename(img_p)}")
            report["is_valid"] = False
            continue

        with open(lbl_p, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines:
            report["empty_images"] += 1
            continue

        report["annotated_images"] += 1

        for idx, line in enumerate(lines, start=1):
            tokens = line.split()
            if len(tokens) != 5:
                report["issues"].append(f"Invalid YOLO line {idx} in {base_name}.txt: '{line}'")
                report["is_valid"] = False
                continue

            try:
                cls_id = int(tokens[0])
                xc, yc, w, h = map(float, tokens[1:])
            except ValueError:
                report["issues"].append(f"Non-numeric coordinates in {base_name}.txt: '{line}'")
                report["is_valid"] = False
                continue

            if cls_id not in ALLOWED_CLASSES:
                report["issues"].append(f"Class ID {cls_id} in {base_name}.txt outside allowed set {ALLOWED_CLASSES}")
                report["is_valid"] = False

            for c_val, c_name in [(xc, "xc"), (yc, "yc"), (w, "w"), (h, "h")]:
                if c_val < 0.0 or c_val > 1.0:
                    report["issues"].append(f"{c_name}={c_val} out of bounds [0, 1] in {base_name}.txt")
                    report["is_valid"] = False

            if w <= 0.0 or h <= 0.0:
                report["issues"].append(f"Degenerate zero-size box in {base_name}.txt: w={w}, h={h}")
                report["is_valid"] = False

            report["total_objects"] += 1
            cls_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")
            report["class_distribution"][cls_name] = report["class_distribution"].get(cls_name, 0) + 1

    return report


def check_leakage(dataset_root: str) -> List[str]:
    splits = ["train", "val", "test"]
    names_by_split = {}
    warnings = []

    for s in splits:
        img_dir = os.path.join(dataset_root, s, "images")
        files = set()
        if os.path.exists(img_dir):
            for f in os.listdir(img_dir):
                if not f.startswith("."):
                    files.add(os.path.splitext(f)[0])
        names_by_split[s] = files

    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            s1, s2 = splits[i], splits[j]
            overlap = names_by_split[s1].intersection(names_by_split[s2])
            if overlap:
                warnings.append(f"CRITICAL LEAKAGE: {len(overlap)} file(s) overlap between {s1} and {s2}: {list(overlap)[:3]}")

    return warnings


def main():
    parser = argparse.ArgumentParser(description="Validate YOLO infrastructure dataset.")
    parser.add_argument("--dataset", default="datasets/infrastructure", help="Path to infrastructure dataset")
    args = parser.parse_args()

    print(f"=== Validating YOLO Infrastructure Dataset at '{args.dataset}' ===")
    summary = {}
    all_valid = True

    for split in ["train", "val", "test"]:
        rep = validate_split(args.dataset, split)
        summary[split] = rep
        if not rep["is_valid"] and rep["total_images"] > 0:
            all_valid = False

        print(f"\n[{split.upper()}] Images: {rep['total_images']} | "
              f"Annotated: {rep['annotated_images']} | "
              f"Empty: {rep['empty_images']} | "
              f"Objects: {rep['total_objects']} | "
              f"Issues: {len(rep['issues'])}")
        print(f"  Class Distribution: {rep['class_distribution']}")

    leakage = check_leakage(args.dataset)
    if leakage:
        print("\n--- Leakage Warnings ---")
        for w in leakage:
            print(f"! {w}")
        all_valid = False
    else:
        print("\n✓ Zero file overlap detected across train, val, and test splits.")

    summary["dataset_valid"] = all_valid
    out_file = os.path.join(args.dataset, "validation_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved validation report to {out_file}")
    print(f"Overall Dataset Valid: {all_valid}")


if __name__ == "__main__":
    main()
