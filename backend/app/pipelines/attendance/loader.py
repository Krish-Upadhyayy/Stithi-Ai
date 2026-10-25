"""Attendance model loading and lifecycle management service."""

import os
import logging
from typing import Optional
from backend.app.core.config import settings
from backend.app.pipelines.attendance.base import AttendanceDetector
from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector
from backend.app.ml.attendance.registry import AttendanceModelRegistry

logger = logging.getLogger(__name__)

_detector_instance: Optional[AttendanceDetector] = None


def get_attendance_detector() -> AttendanceDetector:
    """Retrieves or initializes the global singleton AttendanceDetector instance.
    
    Checks Model Registry for a deployed production model; falls back to configuration.
    Ensures model weights are loaded into memory once rather than per request.
    """
    global _detector_instance
    if _detector_instance is None:
        logger.info("Initializing global YOLO26 AttendanceDetector instance...")
        
        prod_meta = AttendanceModelRegistry.get_production_metadata()
        if prod_meta and os.path.exists(prod_meta.get("weights_path", "")):
            logger.info(f"Loading registered production model: {prod_meta.get('model_name')} ({prod_meta.get('version')})")
            _detector_instance = YOLO26AttendanceDetector(
                model_path=prod_meta.get("weights_path"),
                model_name=prod_meta.get("model_name"),
                model_version=prod_meta.get("version"),
                confidence_threshold=settings.ATTENDANCE_CONFIDENCE_THRESHOLD,
                iou_threshold=settings.ATTENDANCE_IOU_THRESHOLD,
                device=settings.ATTENDANCE_DEVICE,
            )
        else:
            _detector_instance = YOLO26AttendanceDetector(
                model_path=settings.ATTENDANCE_MODEL_PATH,
                model_name=settings.ATTENDANCE_MODEL_NAME,
                model_version=settings.ATTENDANCE_MODEL_VERSION,
                confidence_threshold=settings.ATTENDANCE_CONFIDENCE_THRESHOLD,
                iou_threshold=settings.ATTENDANCE_IOU_THRESHOLD,
                device=settings.ATTENDANCE_DEVICE,
            )

        if _detector_instance.is_available():
            _detector_instance.load_model()
    return _detector_instance


def set_attendance_detector(detector: Optional[AttendanceDetector]) -> None:
    """Overrides or resets the global detector instance.
    
    Useful for testing or dynamic model switching without server restarts.
    """
    global _detector_instance
    _detector_instance = detector
