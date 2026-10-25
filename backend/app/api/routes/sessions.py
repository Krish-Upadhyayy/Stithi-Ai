"""Monitoring Session, Physical Attendance, and Video Snapshot Engine API routes."""

import os
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, UploadFile, File
from starlette import status as http_status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, get_optional_current_user
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.schemas.session import (
    MonitoringSessionCreate,
    MonitoringSessionResponse,
    MonitoringSessionDetailResponse,
)
from backend.app.schemas.snapshot import (
    SnapshotResponse,
    VideoUploadResponse,
    VideoProcessRequest,
    VideoProcessResponse,
)
from backend.app.services.video_service import VideoService

router = APIRouter(tags=["Monitoring Sessions"])



@router.post(
    "/monitoring/sessions",
    response_model=MonitoringSessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a monitoring session with physical attendance baseline",
)
@router.post(
    "/sessions",
    response_model=MonitoringSessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a monitoring session (Legacy route)",
    include_in_schema=False,
)
def create_monitoring_session(
    request: Request,
    session_in: MonitoringSessionCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Initializes a new monitoring session with anonymous physical attendance headcount.
    
    Validates that:
    - The centre exists.
    - The camera exists and belongs to the selected centre.
    - Physical attendance is a non-negative integer.
    - Status is initialized to PENDING.
    - User has permission to create sessions for this centre.
    """
    # Strict authentication check for the /monitoring/sessions endpoint
    if current_user is None:
        if "/monitoring/sessions" in request.url.path:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Role authorization
    if current_user:
        if current_user.role in ["REVIEWER", "AUDITOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Reviewers have read-only access to monitoring sessions.",
            )
        if current_user.role == "CENTRE_USER" and current_user.centre_id:
            if current_user.centre_id != session_in.centre_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You may only create sessions for your assigned centre.",
                )

    # Verify target centre exists
    centre = db.query(Centre).filter(Centre.id == session_in.centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {session_in.centre_id} not found.",
        )

    # Verify target camera exists and belongs to centre
    if session_in.camera_id is None:
        if "/monitoring/sessions" in request.url.path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid camera_id is required to create a monitoring session.",
            )
    else:
        camera = db.query(Camera).filter(Camera.id == session_in.camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera with id {session_in.camera_id} not found.",
            )
        if camera.centre_id != session_in.centre_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera with id {session_in.camera_id} belongs to centre {camera.centre_id}, not centre {session_in.centre_id}.",
            )

    # Validate physical attendance non-negative
    if session_in.physical_attendance < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Physical attendance headcount cannot be negative.",
        )

    # Persist session with initial PENDING status (no video processing or AI inference started)
    session = MonitoringSession(
        centre_id=session_in.centre_id,
        camera_id=session_in.camera_id,
        session_date=session_in.session_date or date.today(),
        physical_attendance=session_in.physical_attendance,
        status="PENDING",
        started_at=None,
        ended_at=None,
        created_by=current_user.id if current_user else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "/monitoring/sessions",
    response_model=List[MonitoringSessionDetailResponse],
    summary="List monitoring sessions with optional filters",
)
@router.get(
    "/sessions",
    response_model=List[MonitoringSessionDetailResponse],
    summary="List monitoring sessions (Legacy route)",
    include_in_schema=False,
)
def list_monitoring_sessions(
    request: Request,
    centre_id: Optional[int] = Query(None, description="Filter sessions by Centre ID"),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, RUNNING, COMPLETED, FAILED"),
    session_date: Optional[date] = Query(None, description="Filter by session calendar date"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieves monitoring sessions filtered by centre, status, or date."""
    if current_user is None and "/monitoring/sessions" in request.url.path:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    query = db.query(MonitoringSession)

    if current_user and current_user.role == "CENTRE_USER" and current_user.centre_id:
        query = query.filter(MonitoringSession.centre_id == current_user.centre_id)
    elif centre_id is not None:
        query = query.filter(MonitoringSession.centre_id == centre_id)

    if status:
        query = query.filter(MonitoringSession.status == status.upper())

    if session_date:
        query = query.filter(MonitoringSession.session_date == session_date)

    sessions = query.order_by(MonitoringSession.id.desc()).all()
    for s in sessions:
        s.snapshots_count = len(s.snapshots)
    return sessions


@router.get(
    "/monitoring/sessions/{session_id}",
    response_model=MonitoringSessionDetailResponse,
    summary="Get details of a monitoring session",
)
@router.get(
    "/sessions/{session_id}",
    response_model=MonitoringSessionDetailResponse,
    summary="Get details of a monitoring session (Legacy route)",
    include_in_schema=False,
)
def get_monitoring_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieves full details of a specific monitoring session."""
    if current_user is None and "/monitoring/sessions" in request.url.path:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user and current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You may only view sessions for your assigned centre.",
            )

    session.snapshots_count = len(session.snapshots)
    return session


@router.post(
    "/monitoring/sessions/{session_id}/start",
    response_model=MonitoringSessionDetailResponse,
    summary="Transition a PENDING monitoring session to RUNNING",
)
@router.post(
    "/sessions/{session_id}/start",
    response_model=MonitoringSessionDetailResponse,
    summary="Start monitoring session (Legacy route)",
    include_in_schema=False,
)
def start_monitoring_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Starts a monitoring session, setting started_at to current timestamp and status to RUNNING.
    
    A session that is already RUNNING, COMPLETED, or FAILED cannot be started again.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user.role in ["REVIEWER", "AUDITOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Reviewers have read-only access to monitoring sessions.",
        )

    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You may only start sessions for your assigned centre.",
            )

    if session.status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is already RUNNING. Cannot start again.",
        )

    if session.status in ["COMPLETED", "FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start session with status '{session.status}'. Only PENDING sessions can be started.",
        )

    if session.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start session with status '{session.status}'. Only PENDING sessions can be started.",
        )

    session.status = "RUNNING"
    session.started_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


@router.post(
    "/monitoring/sessions/{session_id}/complete",
    response_model=MonitoringSessionDetailResponse,
    summary="Transition a RUNNING monitoring session to COMPLETED",
)
@router.post(
    "/sessions/{session_id}/complete",
    response_model=MonitoringSessionDetailResponse,
    summary="Complete monitoring session (Legacy route)",
    include_in_schema=False,
)
def complete_monitoring_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Completes a monitoring session, setting ended_at to current timestamp and status to COMPLETED.
    
    Only RUNNING sessions can be completed.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user.role in ["REVIEWER", "AUDITOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Reviewers have read-only access to monitoring sessions.",
        )

    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You may only complete sessions for your assigned centre.",
            )

    if session.status == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete session with status 'PENDING'. Session must be started and RUNNING first.",
        )

    if session.status != "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete session with status '{session.status}'. Only RUNNING sessions can be completed.",
        )

    session.status = "COMPLETED"
    session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


# ==============================================================
# VIDEO UPLOAD & PERIODIC SNAPSHOT ENGINE ENDPOINTS (Module 8)
# ==============================================================

@router.post(
    "/monitoring/sessions/{session_id}/video",
    response_model=VideoUploadResponse,
    summary="Upload MP4 video for monitoring session",
)
async def upload_session_video(
    session_id: int,
    file: UploadFile = File(..., description="Recorded MP4 video file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Uploads an MP4 video, validates via OpenCV, extracts properties, and associates with the session."""
    if current_user.role in ["REVIEWER", "AUDITOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Reviewers cannot upload video files.",
        )

    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You may only upload videos for your assigned centre.",
            )

    return await VideoService.save_uploaded_video(session=session, file=file, db=db)


@router.post(
    "/monitoring/sessions/{session_id}/process-video",
    response_model=VideoProcessResponse,
    summary="Extract periodic snapshots from uploaded session video",
)
def process_session_video(
    session_id: int,
    process_req: Optional[VideoProcessRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extracts initial (00:00) and periodic snapshots from the session's uploaded MP4 video using OpenCV."""
    if current_user.role in ["REVIEWER", "AUDITOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Reviewers cannot initiate video processing.",
        )

    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You may only process video for your assigned centre.",
            )

    interval = process_req.interval_seconds if process_req else None
    max_snaps = process_req.max_snapshots if process_req else None

    return VideoService.extract_snapshots_for_session(
        session=session,
        interval_seconds=interval,
        max_snapshots=max_snaps,
        db=db,
    )


@router.get(
    "/monitoring/sessions/{session_id}/snapshots",
    response_model=List[SnapshotResponse],
    summary="List extracted snapshots for a monitoring session",
)
def list_session_snapshots(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all extracted snapshots belonging to a monitoring session in chronological sequence."""
    session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session with id {session_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to view snapshots from this centre.",
            )

    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.monitoring_session_id == session_id)
        .order_by(Snapshot.sequence_number.asc())
        .all()
    )

    return [
        SnapshotResponse(
            id=s.id,
            monitoring_session_id=s.monitoring_session_id,
            file_path=s.file_path,
            captured_at=s.captured_at,
            sequence_number=s.sequence_number,
            frame_time_seconds=s.frame_time_seconds,
            width=s.width,
            height=s.height,
            processing_status=s.processing_status,
            created_at=s.created_at,
            view_url=f"/api/v1/monitoring/snapshots/{s.id}/image",
        )
        for s in snapshots
    ]


@router.get(
    "/monitoring/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    summary="Get metadata of an individual snapshot",
)
def get_snapshot_metadata(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves metadata of a specific snapshot."""
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot with id {snapshot_id} not found.",
        )

    session = snapshot.monitoring_session
    if current_user.role == "CENTRE_USER" and current_user.centre_id:
        if session.centre_id != current_user.centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to view this snapshot.",
            )

    return SnapshotResponse(
        id=snapshot.id,
        monitoring_session_id=snapshot.monitoring_session_id,
        file_path=snapshot.file_path,
        captured_at=snapshot.captured_at,
        sequence_number=snapshot.sequence_number,
        frame_time_seconds=snapshot.frame_time_seconds,
        width=snapshot.width,
        height=snapshot.height,
        processing_status=snapshot.processing_status,
        created_at=snapshot.created_at,
        view_url=f"/api/v1/monitoring/snapshots/{snapshot.id}/image",
    )


@router.get(
    "/monitoring/snapshots/{snapshot_id}/image",
    summary="Securely retrieve snapshot JPEG image content",
)
def get_snapshot_image(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely streams snapshot JPEG image content after validating authorization and preventing path traversal."""
    file_path = VideoService.get_secure_snapshot_path(
        snapshot_id=snapshot_id,
        current_user=current_user,
        db=db,
    )
    return FileResponse(
        path=file_path,
        media_type="image/jpeg",
        filename=os.path.basename(file_path),
    )

