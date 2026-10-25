"""Central API v1 router definition."""

from fastapi import APIRouter
from backend.app.api.routes import (
    auth,
    health,
    centres,
    sessions,
    inventory,
    alerts,
    attendance,
    infrastructure,
    compliance,
    dashboard,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(centres.router)
api_router.include_router(sessions.router)
api_router.include_router(inventory.router)
api_router.include_router(alerts.router)
api_router.include_router(attendance.router)
api_router.include_router(infrastructure.router)
api_router.include_router(compliance.router)
api_router.include_router(dashboard.router)
