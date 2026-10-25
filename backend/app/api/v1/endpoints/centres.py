"""Centres endpoint router foundation."""

from fastapi import APIRouter

router = APIRouter(prefix="/centres", tags=["Centres"])


@router.get("", summary="List Training Centres (Foundation)")
def list_centres():
    """Staged endpoint: Entity binding will be completed in Database & Backend Foundation step."""
    return {"message": "Centres endpoint foundation staged", "centres": []}
