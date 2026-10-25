"""Infrastructure AI Pipeline.

Custom YOLO26 object detection pipeline for monitoring sanctioned infrastructure assets.
Strict Constraints (Prompt 11):
- Answers: 'What approved infrastructure/assets are visibly present in snapshots, and approximately how many?'
- Never claims equipment is mechanically functional based on visual detection.
- Decoupled completely from Attendance AI.
"""

from typing import Dict, Any, Optional, Union
import numpy as np

from backend.app.pipelines.infrastructure.base import (
    InfrastructureDetector,
    InfrastructureDetectionResult,
)
from backend.app.pipelines.infrastructure.loader import get_infrastructure_detector


class InfrastructurePipeline:
    """Encapsulates YOLO26-based asset detection and class-wise inventory counting."""

    def __init__(self, detector: Optional[InfrastructureDetector] = None):
        self.detector = detector or get_infrastructure_detector()

    @property
    def is_loaded(self) -> bool:
        return self.detector.is_available()

    def load_model(self) -> bool:
        return self.detector.load_model()

    def detect_assets(
        self,
        image_path_or_array: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        render_annotated: bool = False,
    ) -> InfrastructureDetectionResult:
        """Detect visible infrastructure assets and produce class-wise counts."""
        return self.detector.detect(
            image=image_path_or_array,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            render_annotated=render_annotated,
        )
