"""YOLO26 Infrastructure Asset Detector Adapter.

Wraps the primary YOLO26 object detection model for classroom & training centre assets
(e.g., chairs, computers, projectors, sewing machines, workbenches).
Completely decoupled from Attendance AI.
Strict Constraint: Records visible presence and counts only. Zero claim of mechanical functionality.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Union
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.pipelines.infrastructure.base import (
    InfrastructureDetector,
    InfrastructureDetectionBox,
    InfrastructureDetectionResult,
)
from backend.app.pipelines.infrastructure.mapping import DEFAULT_SUPPORTED_AI_CLASSES

logger = logging.getLogger(__name__)

# Canonical mapping of raw YOLO/COCO object classes to training centre infrastructure assets
COCO_RAW_TO_ASSET_CLASS: Dict[str, str] = {
    "chair": "chair",
    "bench": "chair",
    "couch": "chair",
    "laptop": "computer",
    "tv": "computer",
    "keyboard": "computer",
    "mouse": "computer",
    "dining table": "workbench",
    "workbench": "workbench",
    "computer": "computer",
    "projector": "projector",
    "sewing machine": "sewing machine",
}

# Distinct BGR color palette for recognized asset categories
CLASS_COLORS = {
    "chair": (255, 128, 0),        # Cyan/Blue
    "computer": (0, 200, 255),     # Amber/Orange
    "projector": (0, 255, 128),    # Spring Green
    "sewing machine": (255, 0, 128), # Magenta
    "workbench": (128, 128, 255),  # Coral
}
DEFAULT_BOX_COLOR = (0, 255, 0)


class YOLO26InfrastructureDetector(InfrastructureDetector):
    """Production YOLO26 adapter for infrastructure asset detection."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        device: Optional[str] = None,
        target_classes: Optional[List[str]] = None,
    ):
        self.model_path = model_path or settings.INFRASTRUCTURE_MODEL_PATH
        self.model_name = model_name or settings.INFRASTRUCTURE_MODEL_NAME
        self.model_version = model_version or settings.INFRASTRUCTURE_MODEL_VERSION
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.INFRASTRUCTURE_CONFIDENCE_THRESHOLD
        )
        self.iou_threshold = (
            iou_threshold
            if iou_threshold is not None
            else settings.INFRASTRUCTURE_IOU_THRESHOLD
        )
        self.device = device or settings.INFRASTRUCTURE_DEVICE
        self.target_classes = [c.lower() for c in (target_classes or DEFAULT_SUPPORTED_AI_CLASSES)]
        self._model = None
        self._is_loaded = False

    def is_available(self) -> bool:
        """Returns True if model weights exist at model_path."""
        return bool(self.model_path and os.path.exists(self.model_path))

    def load_model(self) -> bool:
        """Loads and initializes YOLO26 infrastructure model weights into memory once."""
        if self._is_loaded and self._model is not None:
            return True

        if not self.is_available():
            logger.info("Infrastructure AI model weights not found at: %s", self.model_path)
            return False

        try:
            from ultralytics import YOLO
            logger.info("Loading YOLO26 Infrastructure model from %s on %s...", self.model_path, self.device)
            self._model = YOLO(self.model_path)
            self._is_loaded = True
            logger.info("YOLO26 Infrastructure model loaded successfully.")
            return True
        except Exception as e:
            logger.error("Failed to load YOLO26 Infrastructure model: %s", e, exc_info=True)
            self._model = None
            self._is_loaded = False
            return False

    def detect(
        self,
        image: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        render_annotated: bool = False,
    ) -> InfrastructureDetectionResult:
        """Executes YOLO26 asset detection and returns structured counts per class."""
        conf_thresh = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        iou_thresh = iou_threshold if iou_threshold is not None else self.iou_threshold

        if not self.is_available():
            return InfrastructureDetectionResult(
                model_name=self.model_name,
                model_version=self.model_version,
                confidence_threshold=conf_thresh,
                inference_device=self.device,
                status="WEIGHTS_MISSING",
                error_message="Infrastructure AI model is not configured.",
            )

        if not self._is_loaded or self._model is None:
            success = self.load_model()
            if not success:
                return InfrastructureDetectionResult(
                    model_name=self.model_name,
                    model_version=self.model_version,
                    confidence_threshold=conf_thresh,
                    inference_device=self.device,
                    status="WEIGHTS_MISSING",
                    error_message="Infrastructure AI model is not configured.",
                )

        t_start = time.perf_counter()

        try:
            # Read image if file path
            img_to_draw = None
            if isinstance(image, str):
                if not os.path.exists(image):
                    return InfrastructureDetectionResult(
                        model_name=self.model_name,
                        model_version=self.model_version,
                        status="FAILED",
                        error_message=f"Image file not found: {image}",
                    )
                if render_annotated:
                    img_to_draw = cv2.imread(image)
            elif isinstance(image, np.ndarray) and render_annotated:
                img_to_draw = image.copy()

            # Execute YOLO inference
            results = self._model.predict(
                source=image,
                conf=conf_thresh,
                iou=iou_thresh,
                imgsz=getattr(settings, "AI_INFERENCE_IMGSZ", 1280),
                device=self.device,
                verbose=False,
            )

            detections: List[InfrastructureDetectionBox] = []
            class_counts: Dict[str, int] = {}

            if results and len(results) > 0:
                first_res = results[0]
                boxes = first_res.boxes
                names_dict = first_res.names or {}

                if boxes is not None:
                    for i in range(len(boxes)):
                        xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        raw_class_name = str(names_dict.get(cls_id, f"class_{cls_id}")).lower()

                        # Exclude person (handled exclusively by Attendance AI)
                        if raw_class_name == "person":
                            continue

                        # Resolve canonical infrastructure asset category
                        asset_class_name = COCO_RAW_TO_ASSET_CLASS.get(raw_class_name, raw_class_name)

                        # Filter by supported target classes
                        if (
                            asset_class_name in self.target_classes
                            or raw_class_name in self.target_classes
                            or not self.target_classes
                        ):
                            final_class_name = (
                                asset_class_name
                                if (asset_class_name in self.target_classes or not self.target_classes)
                                else raw_class_name
                            )
                            det_box = InfrastructureDetectionBox(
                                bbox=[round(float(c), 2) for c in xyxy],
                                confidence=round(conf, 4),
                                class_name=final_class_name,
                                class_id=cls_id,
                            )
                            detections.append(det_box)
                            class_counts[final_class_name] = class_counts.get(final_class_name, 0) + 1

                            # Draw annotation bounding box on separate copy
                            if render_annotated and img_to_draw is not None:
                                x1, y1, x2, y2 = map(int, xyxy)
                                color = CLASS_COLORS.get(final_class_name, DEFAULT_BOX_COLOR)
                                cv2.rectangle(img_to_draw, (x1, y1), (x2, y2), color, 2)
                                label_text = f"{final_class_name} {conf:.2f}"
                                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                                cv2.rectangle(img_to_draw, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, max(0, y1)), color, -1)
                                cv2.putText(
                                    img_to_draw,
                                    label_text,
                                    (x1 + 2, max(th, y1 - 3)),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.45,
                                    (0, 0, 0),
                                    1,
                                    cv2.LINE_AA,
                                )

            t_end = time.perf_counter()
            inference_time_ms = round((t_end - t_start) * 1000.0, 2)

            return InfrastructureDetectionResult(
                detections=detections,
                class_counts=class_counts,
                model_name=self.model_name,
                model_version=self.model_version,
                inference_time_ms=inference_time_ms,
                inference_device=self.device,
                confidence_threshold=conf_thresh,
                annotated_image=img_to_draw,
                status="SUCCESS",
            )

        except Exception as e:
            logger.error("Inference execution failed on image: %s", e, exc_info=True)
            return InfrastructureDetectionResult(
                model_name=self.model_name,
                model_version=self.model_version,
                inference_device=self.device,
                confidence_threshold=conf_thresh,
                status="FAILED",
                error_message=f"Infrastructure detection failed: {str(e)}",
            )
