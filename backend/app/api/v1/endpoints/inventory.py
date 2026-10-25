"""Sanctioned infrastructure inventory endpoint router foundation."""

from fastapi import APIRouter

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/status", summary="Inventory Service Status")
def get_inventory_status():
    return {
        "service": "inventory",
        "description": "Admin Excel upload (.xlsx) processed with OpenPyXL/Pandas and compared with custom YOLO detections",
        "status": "Staged"
    }
