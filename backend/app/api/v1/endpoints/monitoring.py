"""Monitoring session endpoint router foundation."""

from fastapi import APIRouter

router = APIRouter(prefix="/monitoring", tags=["Monitoring Sessions"])


@router.get("/status", summary="Monitoring Service Status")
def get_monitoring_status():
    return {
        "service": "monitoring",
        "description": "Session orchestration, periodic snapshot capture, and compliance aggregation",
        "status": "Staged"
    }
