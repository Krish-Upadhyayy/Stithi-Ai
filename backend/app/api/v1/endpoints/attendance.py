"""Physical and observed attendance endpoint router foundation."""

from fastapi import APIRouter

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/status", summary="Attendance Pipeline Status")
def get_attendance_status():
    return {
        "pipeline": "attendance",
        "description": "Anonymous head/person count comparison against physical attendance records",
        "status": "Awaiting baseline evaluation"
    }
