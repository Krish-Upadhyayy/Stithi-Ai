"""Aggregated API v1 router."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    centres,
    attendance,
    monitoring,
    inventory,
    alerts,
    dashboard,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(centres.router)
api_router.include_router(attendance.router)
api_router.include_router(monitoring.router)
api_router.include_router(inventory.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
