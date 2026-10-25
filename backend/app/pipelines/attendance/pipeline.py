"""Attendance AI Pipeline foundation.

Anonymous face/head/presence detection pipeline using YOLO26 as the primary model.
Strict Privacy Constraint: Anonymous aggregate counting only. Zero face recognition or biometric identification.
Architecture: Model-swappable interface enabling empirical comparative evaluation against alternative detectors.
"""

from typing import Dict, Any, Optional, Union
import numpy as np

from backend.app.pipelines.attendance.base import AttendanceDetector, AttendanceDetectionResult
from backend.app.pipelines.attendance.loader import get_attendance_detector
from backend.app.pipelines.attendance.yolo26_detector import YOLO26AttendanceDetector


class AttendancePipeline:
    """Encapsulates YOLO26-based anonymous presence detection and aggregate counting.
    
    Designed with a swappable backend to support rigorous empirical evaluation.
    """

    def __init__(self, detector: Optional[AttendanceDetector] = None):
        self.detector = detector or get_attendance_detector()

    @property
    def is_loaded(self) -> bool:
        return self.detector.is_available()

    def load_model(self) -> bool:
        return self.detector.load_model()

    def count_faces(
        self,
        image_path_or_array: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Detect visible individuals and produce an anonymous aggregate count.
        
        Returns count and confidence summaries. Does not fabricate numbers.
        """
        result: AttendanceDetectionResult = self.detector.detect(
            image=image_path_or_array,
            confidence_threshold=confidence_threshold,
        )
        return {
            "detected_count": result.detected_count,
            "confidence_scores": [d.confidence for d in result.detections],
            "avg_confidence": result.avg_confidence,
            "min_confidence": result.min_confidence,
            "max_confidence": result.max_confidence,
            "model_family": "YOLO26",
            "model_name": result.model_name,
            "model_version": result.model_version,
            "inference_time_ms": result.inference_time_ms,
            "status": result.status,
            "message": result.error_message,
        }
