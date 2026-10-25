"""Base interface and data contracts for Attendance Detection AI models.

Strict Privacy Constraint (SRS §FR-03 & PRD §9):
- Anonymous aggregate presence/headcount only.
- Zero face recognition, zero identity vectors, zero facial embeddings.
- Model-swappable architecture for empirical comparative evaluation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any
import numpy as np


@dataclass
class DetectionBox:
    """Represents a single detected human presence bounding box (zero identity)."""
    bbox: List[float]  # [x1, y1, x2, y2] pixel coordinates
    confidence: float
    class_name: str
    class_id: int


@dataclass
class AttendanceDetectionResult:
    """Encapsulates the complete result of an attendance detection inference run."""
    detected_count: int
    detections: List[DetectionBox] = field(default_factory=list)
    model_name: str = "YOLO26-Face-Presence"
    model_version: str = "v1-baseline"
    inference_time_ms: float = 0.0
    inference_device: str = "cpu"
    confidence_threshold: float = 0.40
    avg_confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    annotated_image: Optional[np.ndarray] = None
    status: str = "SUCCESS"  # SUCCESS, WEIGHTS_MISSING, ERROR
    error_message: Optional[str] = None


class AttendanceDetector(ABC):
    """Abstract Base Class for attendance presence detectors.
    
    Enables swapping YOLO26 with future fine-tuned or alternative models
    without altering application logic or API routes.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the detector weights and inference engine are available."""
        pass

    @abstractmethod
    def load_model(self) -> bool:
        """Loads model weights into memory once. Returns True on success."""
        pass

    @abstractmethod
    def detect(
        self,
        image: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        render_annotated: bool = False,
    ) -> AttendanceDetectionResult:
        """Executes presence detection on an image.
        
        Args:
            image: Image filesystem path or OpenCV numpy BGR array.
            confidence_threshold: Optional confidence filter override.
            iou_threshold: Optional IoU suppression threshold override.
            render_annotated: If True, produces an annotated evidence image.
            
        Returns:
            AttendanceDetectionResult with anonymous headcount and metadata.
        """
        pass
