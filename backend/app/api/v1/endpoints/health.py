"""Health check endpoints for the unified Python backend."""

from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.health import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus, summary="System Health Check")
def get_health():
    """Returns the operational status of the unified Python backend and AI pipelines."""
    return HealthStatus(
        status="UP",
        service=settings.APP_NAME,
        environment=settings.APP_ENV,
        architecture="Unified FastAPI + PyTorch/YOLO + MySQL",
        version="0.1.0",
        pipelines={
            "attendance": "ONLINE (Stithi AI anonymous presence evaluation)",
            "infrastructure": "ONLINE (Stithi AI custom asset evaluation)",
            "compliance_engine": "READY (Rule-based comparator operational)",
            "privacy_engine": "READY (Anonymization/blurring utility active)"
        }
    )
