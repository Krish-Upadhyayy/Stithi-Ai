"""Health check route."""

from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.health import HealthStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthStatus, summary="System Health Status")
def get_health():
    """Returns the operational status of the unified Python FastAPI backend."""
    return HealthStatus(
        status="UP",
        service=settings.APP_NAME,
        environment=settings.APP_ENV,
        architecture="FastAPI + SQLAlchemy + MySQL",
        version="0.2.0",
        pipelines={
            "attendance": "ONLINE (Stithi AI anonymous presence evaluation)",
            "infrastructure": "ONLINE (Stithi AI custom asset evaluation)",
            "compliance_engine": "READY (Rule-based comparator operational)",
            "privacy_engine": "READY (Anonymization utility active)",
        }
    )
