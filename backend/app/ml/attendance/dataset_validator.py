"""Dataset Validation & Integrity Analysis for YOLO Attendance Detection.

Checks:
- Image/label pairing
- Format correctness (YOLO 5-tuple: class_id x_center y_center width height)
- Coordinate bounds (0.0 to 1.0)
- Extreme/degenerate bounding boxes
- Empty frames vs annotated frames
- Data leakage prevention across train/val/test splits (session/video-level separation)
"""

import os
import glob
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from PIL import Image


@dataclass
class AnnotationIssue:
    file_path: str
    line_number: int
    issue_type: str
    detail: str


@dataclass
class DatasetValidationReport:
    total_images: int = 0
    annotated_images: int = 0
    empty_images: int = 0
    missing_labels: int = 0
    corrupt_images: int = 0
    total_objects: int = 0
    avg_objects_per_image: float = 0.0
    class_distribution: Dict[int, int] = field(default_factory=dict)
    issues: List[AnnotationIssue] = field(default_factory=list)
    leakage_warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_images": self.total_images,
            "annotated_images": self.annotated_images,
            "empty_images": self.empty_images,
            "missing_labels": self.missing_labels,
            "corrupt_images": self.corrupt_images,
            "total_objects": self.total_objects,
            "avg_objects_per_image": round(self.avg_objects_per_image, 2),
            "class_distribution": self.class_distribution,
            "issues_count": len(self.issues),
            "leakage_warnings": self.leakage_warnings,
            "is_valid": self.is_valid,
        }


class DatasetValidator:
    """Validates YOLO-formatted datasets and verifies absence of train/test leakage."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(self, dataset_root: str = "datasets/attendance", allowed_classes: Optional[Set[int]] = None):
        self.dataset_root = dataset_root
        self.allowed_classes = allowed_classes or {0}  # 0: person/face

    def validate_split(self, split_name: str) -> DatasetValidationReport:
        """Validates an individual split (e.g. 'train', 'val', or 'test')."""
        split_dir = os.path.join(self.dataset_root, split_name)
        images_dir = os.path.join(split_dir, "images")
        labels_dir = os.path.join(split_dir, "labels")

        report = DatasetValidationReport()

        if not os.path.exists(images_dir):
            report.is_valid = False
            return report

        # Collect image files
        image_files = []
        for ext in self.IMAGE_EXTENSIONS:
            image_files.extend(glob.glob(os.path.join(images_dir, f"*{ext}")))
            image_files.extend(glob.glob(os.path.join(images_dir, f"*{ext.upper()}")))

        report.total_images = len(image_files)

        for img_path in image_files:
            # 1. Image integrity check
            try:
                with Image.open(img_path) as img:
                    img.verify()
            except Exception:
                report.corrupt_images += 1
                report.issues.append(
                    AnnotationIssue(
                        file_path=img_path,
                        line_number=0,
                        issue_type="CORRUPT_IMAGE",
                        detail="Cannot open or verify image payload.",
                    )
                )
                continue

            base_name = os.path.splitext(os.path.basename(img_path))[0]
            label_path = os.path.join(labels_dir, f"{base_name}.txt")

            # 2. Label presence check
            if not os.path.exists(label_path):
                report.missing_labels += 1
                report.issues.append(
                    AnnotationIssue(
                        file_path=img_path,
                        line_number=0,
                        issue_type="MISSING_LABEL",
                        detail=f"Expected label file {base_name}.txt not found.",
                    )
                )
                continue

            # 3. Read and validate annotations
            with open(label_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not lines:
                report.empty_images += 1
                continue

            report.annotated_images += 1
            for line_idx, line in enumerate(lines, start=1):
                tokens = line.split()
                if len(tokens) != 5:
                    report.issues.append(
                        AnnotationIssue(
                            file_path=label_path,
                            line_number=line_idx,
                            issue_type="MALFORMED_YOLO_TUPLE",
                            detail=f"Expected 5 tokens (class x y w h), found {len(tokens)}: '{line}'",
                        )
                    )
                    report.is_valid = False
                    continue

                try:
                    cls_id = int(tokens[0])
                    xc, yc, w, h = map(float, tokens[1:])
                except ValueError:
                    report.issues.append(
                        AnnotationIssue(
                            file_path=label_path,
                            line_number=line_idx,
                            issue_type="NON_NUMERIC_COORDINATE",
                            detail=f"Non-numeric values in line: '{line}'",
                        )
                    )
                    report.is_valid = False
                    continue

                # Class validation
                if cls_id not in self.allowed_classes:
                    report.issues.append(
                        AnnotationIssue(
                            file_path=label_path,
                            line_number=line_idx,
                            issue_type="DISALLOWED_CLASS_ID",
                            detail=f"Class ID {cls_id} not in allowed set {self.allowed_classes}.",
                        )
                    )
                    report.is_valid = False

                # Coordinate bounds validation [0.0, 1.0]
                coords_valid = True
                for name, val in [("x_center", xc), ("y_center", yc), ("width", w), ("height", h)]:
                    if val < 0.0 or val > 1.0:
                        report.issues.append(
                            AnnotationIssue(
                                file_path=label_path,
                                line_number=line_idx,
                                issue_type="OUT_OF_BOUNDS_COORDINATE",
                                detail=f"{name}={val} is outside [0.0, 1.0].",
                            )
                        )
                        coords_valid = False
                        report.is_valid = False

                # Degenerate zero-size box check
                if w <= 0.0 or h <= 0.0:
                    report.issues.append(
                        AnnotationIssue(
                            file_path=label_path,
                            line_number=line_idx,
                            issue_type="DEGENERATE_BOX",
                            detail=f"Zero or negative dimension: w={w}, h={h}.",
                        )
                    )
                    coords_valid = False
                    report.is_valid = False

                if coords_valid:
                    report.total_objects += 1
                    report.class_distribution[cls_id] = report.class_distribution.get(cls_id, 0) + 1

        if report.total_images > 0:
            report.avg_objects_per_image = report.total_objects / report.total_images

        if report.issues:
            report.is_valid = False

        return report

    def check_leakage_between_splits(self) -> List[str]:
        """Detects data leakage between train, val, and test splits.
        
        Checks:
        1. Duplicate image basenames across splits.
        2. Video/session prefix leakage (e.g. video1_001 in train and video1_002 in test).
        """
        splits = ["train", "val", "test"]
        split_basenames: Dict[str, Set[str]] = {}
        split_session_prefixes: Dict[str, Set[str]] = {}
        warnings: List[str] = []

        for s in splits:
            img_dir = os.path.join(self.dataset_root, s, "images")
            basenames = set()
            prefixes = set()
            if os.path.exists(img_dir):
                for f in os.listdir(img_dir):
                    base = os.path.splitext(f)[0]
                    if base and not base.startswith("."):
                        basenames.add(base)
                        # Extract session/video prefix (e.g., session_12_snap_0001 -> session_12)
                        parts = base.split("_")
                        if len(parts) >= 2:
                            prefixes.add("_".join(parts[:2]))
            split_basenames[s] = basenames
            split_session_prefixes[s] = prefixes

        # Check identical file overlaps
        for i in range(len(splits)):
            for j in range(i + 1, len(splits)):
                s1, s2 = splits[i], splits[j]
                overlap = split_basenames[s1].intersection(split_basenames[s2])
                if overlap:
                    warnings.append(
                        f"CRITICAL LEAKAGE: {len(overlap)} identical file(s) present in both '{s1}' and '{s2}': {list(overlap)[:3]}"
                    )

        # Check session/source prefix overlaps between train and test
        train_test_prefix_overlap = split_session_prefixes["train"].intersection(split_session_prefixes["test"])
        if train_test_prefix_overlap:
            warnings.append(
                f"POTENTIAL SEQUENCE LEAKAGE: Session/video prefix(es) {list(train_test_prefix_overlap)} appear in both train and test splits."
            )

        return warnings

    def validate_full_dataset(self) -> Dict[str, Any]:
        """Runs validation across all splits and checks for cross-split leakage."""
        summary = {}
        all_valid = True

        for split in ["train", "val", "test"]:
            rep = self.validate_split(split)
            summary[split] = rep.to_dict()
            if not rep.is_valid and rep.total_images > 0:
                all_valid = False

        leakage_warnings = self.check_leakage_between_splits()
        if any("CRITICAL LEAKAGE" in w for w in leakage_warnings):
            all_valid = False

        summary["leakage_warnings"] = leakage_warnings
        summary["dataset_valid"] = all_valid
        return summary
