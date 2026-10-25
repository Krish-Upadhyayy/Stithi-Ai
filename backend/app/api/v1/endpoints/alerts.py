"""Compliance alerts endpoint router foundation."""

from fastapi import APIRouter

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", summary="List Discrepancy Alerts (Foundation)")
def list_alerts():
    return {
        "alerts": [],
        "description": "Evidence-backed alerts for attendance and infrastructure discrepancies",
        "status": "Staged"
    }
