"""Full Evaluation Pipeline for YOLO26 Attendance Presence Detection.

Evaluates both:
1. Object Detection Metrics (Precision, Recall, F1, mAP@50, True/False Positives).
2. Attendance Headcount Metrics (Count MAE, RMSE, Exact Match %, Within +/-1 %, Within +/-2 %).
"""

import os
import glob
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

from backend.app.pipelines.attendance.base import AttendanceDetector
from backend.app.ml.attendance.count_metrics import (
    ImageCountEvaluation,
    AttendanceCountEvaluator,
    AttendanceCountMetricsReport,
)


def compute_iou(boxA: List[float], boxB: List[float]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])

    union = boxAArea + boxBArea - interArea
    if union <= 0.0:
        return 0.0
    return interArea / union


class AttendanceModelEvaluator:
    """Runs rigorous empirical evaluation of an AttendanceDetector on a dataset split."""

    def __init__(self, detector: AttendanceDetector):
        self.detector = detector

    def evaluate_split(
        self,
        dataset_root: str,
        split_name: str = "test",
        confidence_threshold: Optional[float] = None,
        iou_match_threshold: float = 0.50,
    ) -> Dict[str, Any]:
        """Runs evaluation over all images in the specified dataset split."""
        split_dir = os.path.join(dataset_root, split_name)
        images_dir = os.path.join(split_dir, "images")
        labels_dir = os.path.join(split_dir, "labels")

        if not os.path.exists(images_dir):
            return {
                "status": "DATASET_NOT_FOUND",
                "message": f"Images directory not found at {images_dir}",
                "split": split_name,
            }

        image_files = sorted(
            glob.glob(os.path.join(images_dir, "*.jpg"))
            + glob.glob(os.path.join(images_dir, "*.jpeg"))
            + glob.glob(os.path.join(images_dir, "*.png"))
        )

        if not image_files:
            return {
                "status": "EMPTY_DATASET",
                "message": f"No image files found in {images_dir}",
                "split": split_name,
            }

        conf_thresh = confidence_threshold or getattr(self.detector, "confidence_threshold", 0.40)

        total_tp = 0
        total_fp = 0
        total_fn = 0
        inference_times = []
        count_evaluations: List[ImageCountEvaluation] = []
        all_image_boxes: List[Any] = []

        for img_path in image_files:
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            label_path = os.path.join(labels_dir, f"{base_name}.txt")

            # 1. Parse Ground Truth
            gt_boxes: List[List[float]] = []  # xyxy normalized or absolute
            if os.path.exists(label_path):
                # We need image dimensions to convert YOLO normalized xc,yc,w,h to xyxy pixel or normalized
                with open(label_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            xc, yc, w, h = map(float, parts[1:])
                            x1 = xc - w / 2.0
                            y1 = yc - h / 2.0
                            x2 = xc + w / 2.0
                            y2 = yc + h / 2.0
                            gt_boxes.append([x1, y1, x2, y2])

            actual_count = len(gt_boxes)

            # 2. Run Model Inference
            t0 = time.perf_counter()
            result = self.detector.detect(
                image=img_path,
                confidence_threshold=conf_thresh,
            )
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000.0
            inference_times.append(latency_ms)

            predicted_count = result.detected_count
            count_evaluations.append(
                ImageCountEvaluation(
                    image_name=os.path.basename(img_path),
                    actual_count=actual_count,
                    predicted_count=predicted_count,
                )
            )

            # 3. Match Detections with Ground Truth for Object Detection Metrics
            pred_boxes = []
            for det in result.detections:
                # If det.bbox is in pixel coordinates and gt_boxes is normalized, normalize or keep relative
                # For robust matching, compute relative IoU if gt is normalized
                # We'll normalize pred_boxes if max coordinate > 1.0
                b = det.bbox
                if max(b) > 1.0:
                    # Normalized by image size if we can inspect or assume standard shape
                    # For simple evaluation, result bbox matches image resolution
                    try:
                        from PIL import Image
                        with Image.open(img_path) as im:
                            w_img, h_img = im.size
                        pred_boxes.append([b[0] / w_img, b[1] / h_img, b[2] / w_img, b[3] / h_img])
                    except Exception:
                        pred_boxes.append(b)
                else:
                    pred_boxes.append(b)

            all_image_boxes.append((pred_boxes, gt_boxes))

            matched_gt = set()
            img_tp = 0
            img_fp = 0

            for p_box in pred_boxes:
                best_iou = 0.0
                best_gt_idx = -1
                for gt_idx, g_box in enumerate(gt_boxes):
                    if gt_idx in matched_gt:
                        continue
                    iou = compute_iou(p_box, g_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = gt_idx

                if best_iou >= iou_match_threshold and best_gt_idx >= 0:
                    matched_gt.add(best_gt_idx)
                    img_tp += 1
                else:
                    img_fp += 1

            img_fn = actual_count - len(matched_gt)
            total_tp += img_tp
            total_fp += img_fp
            total_fn += img_fn

        # 4. Compute Object Detection Metrics & Multi-threshold mAP@50:95
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        iou_thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
        map_scores = []
        for thresh in iou_thresholds:
            tp_t, fp_t, fn_t = 0, 0, 0
            for pred_b_list, gt_b_list in all_image_boxes:
                matched = set()
                for p_box in pred_b_list:
                    best_iou = 0.0
                    best_idx = -1
                    for g_idx, g_box in enumerate(gt_b_list):
                        if g_idx in matched:
                            continue
                        iou = compute_iou(p_box, g_box)
                        if iou > best_iou:
                            best_iou = iou
                            best_idx = g_idx
                    if best_iou >= thresh and best_idx >= 0:
                        matched.add(best_idx)
                        tp_t += 1
                    else:
                        fp_t += 1
                fn_t += len(gt_b_list) - len(matched)
            p_t = tp_t / (tp_t + fp_t) if (tp_t + fp_t) > 0 else 0.0
            r_t = tp_t / (tp_t + fn_t) if (tp_t + fn_t) > 0 else 0.0
            map_scores.append(p_t * r_t)

        map50 = map_scores[0]
        map50_95 = sum(map_scores) / len(map_scores) if map_scores else 0.0

        avg_latency = float(np.mean(inference_times)) if inference_times else 0.0
        fps = (1000.0 / avg_latency) if avg_latency > 0 else 0.0

        # 5. Compute Attendance Count Metrics
        count_report: AttendanceCountMetricsReport = AttendanceCountEvaluator.compute_metrics(count_evaluations)

        return {
            "status": "SUCCESS",
            "evaluation_date": datetime.utcnow().isoformat(),
            "model_name": getattr(self.detector, "model_name", "YOLO26-Attendance"),
            "model_version": getattr(self.detector, "model_version", "baseline"),
            "split": split_name,
            "images_evaluated": len(image_files),
            "confidence_threshold": conf_thresh,
            "iou_threshold": iou_match_threshold,
            "detection_metrics": {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "map50": round(map50, 4),
                "map50_95": round(map50_95, 4),
                "true_positives": total_tp,
                "false_positives": total_fp,
                "false_negatives": total_fn,
            },
            "speed_metrics": {
                "avg_inference_time_ms": round(avg_latency, 2),
                "fps": round(fps, 1),
            },
            "count_metrics": count_report.to_dict(),
        }
