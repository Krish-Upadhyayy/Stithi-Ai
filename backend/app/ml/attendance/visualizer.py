"""Visual Evaluation Utility for Ground Truth vs Prediction Comparison.

Generates overlay images showing:
- Green boxes: Ground Truth (verified human presence)
- Cyan boxes: Model Predictions (YOLO26 detection)
"""

import os
from typing import List
import cv2
import numpy as np


class EvaluationVisualizer:
    """Renders visual verification images for qualitative detection inspection."""

    @staticmethod
    def render_overlay(
        image_path: str,
        gt_boxes_xyxy: List[List[float]],
        pred_boxes_xyxy: List[List[float]],
        output_dir: str = "storage/evidence/eval_visualizations",
        output_filename: str = "eval_overlay.jpg",
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)
        img = cv2.imread(image_path)
        if img is None:
            return ""

        h, w = img.shape[:2]

        # Draw Ground Truth in Green
        for box in gt_boxes_xyxy:
            if max(box) <= 1.0:
                x1, y1, x2, y2 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
            else:
                x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, "GT", (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # Draw Predictions in Cyan
        for box in pred_boxes_xyxy:
            if max(box) <= 1.0:
                x1, y1, x2, y2 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
            else:
                x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(img, "Pred", (x1, max(15, y2 + 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        out_path = os.path.join(output_dir, output_filename)
        cv2.imwrite(out_path, img)
        return out_path
