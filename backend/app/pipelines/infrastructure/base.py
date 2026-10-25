"""Base abstractions for Infrastructure AI Detection Pipeline.

Strict Constraint: Evaluates visible asset presence and counts only.
Zero claim of mechanical/electrical equipment functionality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import numpy as np


@dataclass
class InfrastructureDetectionBox:
    """Individual detected infrastructure asset bounding box."""
    bbox: List[float]  # [x1, y1, x2, y2] pixel coordinates
    confidence: float
    class_name: str    # e.g., chair, computer, projector
    class_id: int


@dataclass
class InfrastructureDetectionResult:
    """Consolidated detection results for a single snapshot."""
    detections: List[InfrastructureDetectionBox] = field(default_factory=list)
    class_counts: Dict[str, int] = field(default_factory=dict)
    model_name: str = "YOLO26-Infrastructure"
    model_version: str = "v1-baseline"
    inference_time_ms: float = 0.0
    inference_device: str = "cpu"
    confidence_threshold: float = 0.40
    annotated_image: Optional[np.ndarray] = None
    status: str = "SUCCESS"  # SUCCESS, WEIGHTS_MISSING, FAILED
    error_message: Optional[str] = None

    @property
    def total_detected_assets(self) -> int:
        return sum(self.class_counts.values())

    def get_class_confidence_stats(self, class_name: str) -> Dict[str, Optional[float]]:
        scores = [d.confidence for d in self.detections if d.class_name.lower() == class_name.lower()]
        if not scores:
            return {"avg": None, "min": None, "max": None}
        return {
            "avg": round(float(np.mean(scores)), 4),
            "min": round(float(min(scores)), 4),
            "max": round(float(max(scores)), 4),
        }


class InfrastructureDetector(ABC):
    """Abstract Base Class for swappable Infrastructure Detection models."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if model weights exist and are loadable."""
        pass

    @abstractmethod
    def load_model(self) -> bool:
        """Initializes and caches model weights in memory."""
        pass

    @abstractmethod
    def detect(
        self,
        image: Union[str, np.ndarray],
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        render_annotated: bool = False,
    ) -> InfrastructureDetectionResult:
        """Executes asset detection inference on an image path or RGB array."""
        pass
