"""Infrastructure model loading and lifecycle management service."""

import logging
from typing import Optional
from backend.app.core.config import settings
from backend.app.pipelines.infrastructure.base import InfrastructureDetector
from backend.app.pipelines.infrastructure.yolo26_detector import YOLO26InfrastructureDetector

logger = logging.getLogger(__name__)

_infrastructure_detector_instance: Optional[InfrastructureDetector] = None


def get_infrastructure_detector() -> InfrastructureDetector:
    """Retrieves or initializes the global singleton InfrastructureDetector instance.
    
    Ensures model weights are loaded into memory once rather than per request.
    Decoupled entirely from Attendance AI.
    """
    global _infrastructure_detector_instance
    if _infrastructure_detector_instance is None:
        logger.info("Initializing global YOLO26 InfrastructureDetector instance...")
        _infrastructure_detector_instance = YOLO26InfrastructureDetector(
            model_path=settings.INFRASTRUCTURE_MODEL_PATH,
            model_name=settings.INFRASTRUCTURE_MODEL_NAME,
            model_version=settings.INFRASTRUCTURE_MODEL_VERSION,
            confidence_threshold=settings.INFRASTRUCTURE_CONFIDENCE_THRESHOLD,
            iou_threshold=settings.INFRASTRUCTURE_IOU_THRESHOLD,
            device=settings.INFRASTRUCTURE_DEVICE,
        )

        if _infrastructure_detector_instance.is_available():
            _infrastructure_detector_instance.load_model()

    return _infrastructure_detector_instance


def set_infrastructure_detector(detector: Optional[InfrastructureDetector]) -> None:
    """Overrides or resets the global infrastructure detector instance.
    
    Useful for testing or dynamic model switching without server restarts.
    """
    global _infrastructure_detector_instance
    _infrastructure_detector_instance = detector
