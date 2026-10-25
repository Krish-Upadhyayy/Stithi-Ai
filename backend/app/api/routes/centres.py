"""Training Centre and Camera management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import require_authenticated_user, require_role
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.schemas.centre import (
    CentreCreate,
    CentreUpdate,
    CentreStatusUpdate,
    CentreResponse,
)
from backend.app.schemas.camera import (
    CameraCreate,
    CameraUpdate,
    CameraStatusUpdate,
    CameraResponse,
)

router = APIRouter(prefix="/centres", tags=["Centres & Cameras"])


# ==============================================================
# CENTRE ENDPOINTS
# ==============================================================

@router.get("", response_model=List[CentreResponse], summary="List all centres")
def list_centres(
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Retrieves training centres according to authenticated user role."""
    query = db.query(Centre)
    # If centre-specific user is bound to a single centre, restrict results
    if current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        query = query.filter(Centre.id == current_user.centre_id)

    return query.order_by(Centre.id.asc()).all()


@router.post(
    "",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new centre (Admin only)",
)
def create_centre(
    centre_in: CentreCreate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Registers a new training centre with a unique centre code."""
    existing = db.query(Centre).filter(Centre.centre_code == centre_in.centre_code.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Centre with code '{centre_in.centre_code}' already exists.",
        )

    centre = Centre(
        centre_code=centre_in.centre_code.strip(),
        name=centre_in.name.strip(),
        location=centre_in.location.strip() if centre_in.location else None,
        status=centre_in.status,
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("/{centre_id}", response_model=CentreResponse, summary="Get centre details")
def get_centre(
    centre_id: int,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Retrieves a single training centre by ID."""
    if current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        if current_user.centre_id != centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You can only view your assigned centre.",
            )

    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )
    return centre


@router.put(
    "/{centre_id}",
    response_model=CentreResponse,
    summary="Update centre information (Admin only)",
)
def update_centre(
    centre_id: int,
    centre_in: CentreUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Updates training centre metadata and configuration."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    if centre_in.centre_code is not None:
        new_code = centre_in.centre_code.strip()
        if new_code != centre.centre_code:
            existing = (
                db.query(Centre)
                .filter(Centre.centre_code == new_code, Centre.id != centre_id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Centre code '{new_code}' is already assigned to another centre.",
                )
            centre.centre_code = new_code

    if centre_in.name is not None:
        centre.name = centre_in.name.strip()
    if centre_in.location is not None:
        centre.location = centre_in.location.strip()
    if centre_in.status is not None:
        centre.status = centre_in.status

    db.commit()
    db.refresh(centre)
    return centre


@router.patch(
    "/{centre_id}/status",
    response_model=CentreResponse,
    summary="Activate / Deactivate centre (Admin only)",
)
def update_centre_status(
    centre_id: int,
    status_in: CentreStatusUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Toggles active/inactive operational status for a centre."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    centre.status = status_in.status
    db.commit()
    db.refresh(centre)
    return centre


@router.delete(
    "/{centre_id}",
    summary="Safely deactivate centre (Admin only)",
)
def delete_centre(
    centre_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Safely deactivates a training centre to preserve historical compliance integrity."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    centre.status = "INACTIVE"
    db.commit()
    return {
        "message": f"Centre {centre_id} has been deactivated successfully.",
        "id": centre_id,
        "status": "INACTIVE",
    }


# ==============================================================
# CAMERA ENDPOINTS (Scoped under /centres/{centre_id}/cameras)
# ==============================================================

@router.get(
    "/{centre_id}/cameras",
    response_model=List[CameraResponse],
    summary="List cameras belonging to a centre",
)
def list_centre_cameras(
    centre_id: int,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Retrieves all cameras registered to a given training centre."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        if current_user.centre_id != centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view cameras from this centre.",
            )

    cameras = db.query(Camera).filter(Camera.centre_id == centre_id).order_by(Camera.id.asc()).all()
    return cameras


@router.post(
    "/{centre_id}/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new camera for a centre (Admin only)",
)
def create_camera(
    centre_id: int,
    camera_in: CameraCreate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Registers a camera source (MP4 video path or camera stream) associated with a centre."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    camera = Camera(
        centre_id=centre_id,
        name=camera_in.name.strip(),
        source_type=camera_in.source_type,
        source_url=camera_in.source_url.strip(),
        is_active=camera_in.is_active,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.get(
    "/{centre_id}/cameras/{camera_id}",
    response_model=CameraResponse,
    summary="Get camera details",
)
def get_camera(
    centre_id: int,
    camera_id: int,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Retrieves camera details while enforcing strict centre association."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        if current_user.centre_id != centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view cameras from this centre.",
            )

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id, Camera.centre_id == centre_id)
        .first()
    )
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found in centre {centre_id}.",
        )
    return camera


@router.put(
    "/{centre_id}/cameras/{camera_id}",
    response_model=CameraResponse,
    summary="Update camera configuration (Admin only)",
)
def update_camera(
    centre_id: int,
    camera_id: int,
    camera_in: CameraUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Updates camera configuration while verifying centre ownership."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id, Camera.centre_id == centre_id)
        .first()
    )
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found in centre {centre_id}.",
        )

    if camera_in.name is not None:
        camera.name = camera_in.name.strip()
    if camera_in.source_type is not None:
        camera.source_type = camera_in.source_type
    if camera_in.source_url is not None:
        camera.source_url = camera_in.source_url.strip()
    if camera_in.is_active is not None:
        camera.is_active = camera_in.is_active

    db.commit()
    db.refresh(camera)
    return camera


@router.patch(
    "/{centre_id}/cameras/{camera_id}/status",
    response_model=CameraResponse,
    summary="Activate / Deactivate camera (Admin only)",
)
def update_camera_status(
    centre_id: int,
    camera_id: int,
    status_in: CameraStatusUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Toggles active/inactive state of a camera."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id, Camera.centre_id == centre_id)
        .first()
    )
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found in centre {centre_id}.",
        )

    camera.is_active = status_in.is_active
    db.commit()
    db.refresh(camera)
    return camera
