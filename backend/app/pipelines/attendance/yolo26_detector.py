"""YOLO26-based anonymous presence detector for attendance counting.

Primary model generation: YOLO26.
Strict Privacy Constraint (SRS §FR-03 & PRD §9):
- Anonymous aggregate headcount only.
- Zero face recognition or biometric identification.
- Bounding box evidence for visual audit without identity profiling.
"""

import os
import time
import logging
from typing import Optional, Union, List
import numpy as np
import cv2

from backend.app.core.config import settings
from backend.app.pipelines.attendance.base import (
    AttendanceDetector,
    DetectionBox,
    AttendanceDetectionResult,
)

logger = logging.getLogger(__name__)


class YOLO26AttendanceDetector(AttendanceDetector):
    """YOLO26 detector implementation for anonymous presence and face/head counting."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        device: Optional[str] = None,
    ):
        self.model_path = model_path or settings.ATTENDANCE_MODEL_PATH
        self.model_name = model_name or settings.ATTENDANCE_MODEL_NAME
        self.model_version = model_version or settings.ATTENDANCE_MODEL_VERSION
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.ATTENDANCE_CONFIDENCE_THRESHOLD
        )
        self.iou_threshold = (
            iou_threshold
            if iou_threshold is not None
            else settings.ATTENDANCE_IOU_THRESHOLD
        )
        self.device = device or settings.ATTENDANCE_DEVICE
        self._model = None
        self._load_attempted = False

    def is_available(self) -> bool:
        """Returns True if the weights file exists on disk."""
        if not self.model_path:
            return False
        return os.path.exists(self.model_path)

    def load_model(self) -> bool:
        """Loads YOLO26 weights into memory once.
        
        Avoids repeatedly loading weights across requests.
        """
        if self._model is not None:
            return True

        if not self.is_available():
            logger.warning(
                f"YOLO26 Attendance weights not found at path: {self.model_path}. "
                "Attendance AI is in unconfigured state."
            )
            return False

        try:
            from ultralytics import YOLO  # lazy import
            logger.info(f"Loading YOLO26 Attendance model from {self.model_path} onto {self.device}...")
            self._model = YOLO(self.model_path)
            self._load_attempted = True
            logger.info("YOLO26 Attendance model successfully loaded.")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO26 weights from {self.model_path}: {e}")
            self._model = None
            return False

    def detect(
        self,
        image: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        render_annotated: bool = False,
    ) -> AttendanceDetectionResult:
        """Runs anonymous presence detection on image.
        
        Answers: 'How many people appear to be present in this snapshot?'
        Never answers: 'Which student is this?'
        """
        conf_thresh = (
            confidence_threshold
            if confidence_threshold is not None
            else self.confidence_threshold
        )
        iou_thresh = (
            iou_threshold if iou_threshold is not None else self.iou_threshold
        )

        # 1. Check if model weights are available
        if not self.is_available():
            return AttendanceDetectionResult(
                detected_count=0,
                detections=[],
                model_name=self.model_name,
                model_version=self.model_version,
                inference_time_ms=0.0,
                inference_device=self.device,
                confidence_threshold=conf_thresh,
                status="WEIGHTS_MISSING",
                error_message=f"Attendance AI model weights not configured or missing at '{self.model_path}'.",
            )

        # 2. Ensure model is loaded into memory
        if self._model is None:
            loaded = self.load_model()
            if not loaded or self._model is None:
                return AttendanceDetectionResult(
                    detected_count=0,
                    detections=[],
                    model_name=self.model_name,
                    model_version=self.model_version,
                    inference_time_ms=0.0,
                    inference_device=self.device,
                    confidence_threshold=conf_thresh,
                    status="ERROR",
                    error_message="Failed to initialize YOLO26 model engine.",
                )

        # 3. Load or validate image
        img_for_inference = image
        img_bgr = None
        if isinstance(image, str):
            if not os.path.exists(image):
                return AttendanceDetectionResult(
                    detected_count=0,
                    detections=[],
                    model_name=self.model_name,
                    model_version=self.model_version,
                    inference_time_ms=0.0,
                    inference_device=self.device,
                    confidence_threshold=conf_thresh,
                    status="ERROR",
                    error_message=f"Image file does not exist: {image}",
                )
            if render_annotated:
                img_bgr = cv2.imread(image)
        elif isinstance(image, np.ndarray):
            if render_annotated:
                img_bgr = image.copy()

        # 4. Run inference with timing
        t_start = time.perf_counter()
        try:
            results = self._model.predict(
                source=img_for_inference,
                conf=conf_thresh,
                iou=iou_thresh,
                imgsz=getattr(settings, "AI_INFERENCE_IMGSZ", 1280),
                device=self.device,
                verbose=False,
            )
            t_end = time.perf_counter()
            inference_time_ms = round((t_end - t_start) * 1000.0, 2)
        except Exception as e:
            logger.error(f"Inference error in YOLO26 attendance detector: {e}")
            return AttendanceDetectionResult(
                detected_count=0,
                detections=[],
                model_name=self.model_name,
                model_version=self.model_version,
                inference_time_ms=0.0,
                inference_device=self.device,
                confidence_threshold=conf_thresh,
                status="ERROR",
                error_message=f"Inference execution failed: {str(e)}",
            )

        # 5. Extract detections
        detections: List[DetectionBox] = []
        confidences: List[float] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    cls_name = result.names.get(cls_id, f"class_{cls_id}")
                    conf = float(box.conf[0].item())

                    # Check for generic human presence classes (person, face, head)
                    # We accept 'person' (COCO class 0) or 'face' (face model class 0)
                    is_presence_class = (
                        cls_name.lower() in ["person", "face", "head"]
                        or cls_id == 0
                    )

                    if is_presence_class and conf >= conf_thresh:
                        xyxy = [round(float(coord), 1) for coord in box.xyxy[0].tolist()]
                        detections.append(
                            DetectionBox(
                                bbox=xyxy,
                                confidence=round(conf, 4),
                                class_name="person",  # Normalized generic label
                                class_id=cls_id,
                            )
                        )
                        confidences.append(conf)

        # 6. Calculate aggregate stats
        detected_count = len(detections)
        avg_conf = round(float(np.mean(confidences)), 4) if confidences else None
        min_conf = round(float(np.min(confidences)), 4) if confidences else None
        max_conf = round(float(np.max(confidences)), 4) if confidences else None

        # 7. Render optional annotated image
        annotated_img = None
        if render_annotated and img_bgr is not None:
            annotated_img = img_bgr.copy()
            for det in detections:
                x1, y1, x2, y2 = [int(v) for v in det.bbox]
                # Draw bounding box (emerald green)
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 220, 110), 2)
                label = f"Person {det.confidence:.2f}"
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(
                    annotated_img,
                    (x1, max(0, y1 - lh - 4)),
                    (x1 + lw + 4, max(lh + 4, y1)),
                    (0, 220, 110),
                    -1,
                )
                cv2.putText(
                    annotated_img,
                    label,
                    (x1 + 2, max(lh, y1 - 2)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 0, 0),
                    1,
                    cv2.LINE_AA,
                )

        return AttendanceDetectionResult(
            detected_count=detected_count,
            detections=detections,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_time_ms=inference_time_ms,
            inference_device=self.device,
            confidence_threshold=conf_thresh,
            avg_confidence=avg_conf,
            min_confidence=min_conf,
            max_confidence=max_conf,
            annotated_image=annotated_img,
            status="SUCCESS",
        )
