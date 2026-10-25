"""Video and Snapshot Engine service layer."""

import os
import shutil
import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.user import User
from backend.app.schemas.snapshot import VideoUploadResponse, VideoProcessResponse, SnapshotResponse
from backend.app.video.snapshot_extractor import SnapshotExtractor, VideoProcessingError

logger = logging.getLogger(__name__)


class VideoService:
    """Orchestrates video upload storage, OpenCV metadata extraction, and snapshot persistence."""

    @staticmethod
    def _get_storage_root() -> str:
        root = os.path.abspath(settings.STORAGE_ROOT)
        os.makedirs(root, exist_ok=True)
        return root

    @classmethod
    def get_video_dir_for_session(cls, session_id: int) -> str:
        storage_root = cls._get_storage_root()
        path = os.path.join(storage_root, settings.VIDEO_DIR, f"session_{session_id}")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def get_snapshot_dir_for_session(cls, session_id: int) -> str:
        storage_root = cls._get_storage_root()
        path = os.path.join(storage_root, settings.SNAPSHOT_DIR, f"session_{session_id}")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    async def save_uploaded_video(
        cls,
        session: MonitoringSession,
        file: UploadFile,
        db: Session,
    ) -> VideoUploadResponse:
        """Saves uploaded MP4 file to isolated storage, validates via OpenCV, and saves metadata.
        
        Security checks:
        - Extension verification (.mp4)
        - Safe randomized filename (prevents path traversal / overwrite)
        - Size enforcement (< MAX_VIDEO_FILE_SIZE_BYTES)
        - OpenCV inspection (detects corrupted/fake/empty files)
        """
        # 1. Validate file extension
        orig_filename = file.filename or "video.mp4"
        ext = os.path.splitext(orig_filename)[1].lower()
        if ext != ".mp4":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported video file extension '{ext}'. Only .mp4 files are accepted.",
            )

        # 2. Check content type (allowing standard video/mp4 and octet-stream)
        content_type = (file.content_type or "").lower()
        if content_type and not (
            content_type.startswith("video/") or content_type == "application/octet-stream"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type '{file.content_type}'. Must be video/mp4.",
            )

        # 3. Prepare target destination
        session_video_dir = cls.get_video_dir_for_session(session.id)
        safe_filename = f"source_{uuid.uuid4().hex[:12]}.mp4"
        destination_path = os.path.join(session_video_dir, safe_filename)

        # 4. Stream write in chunks and enforce file size
        total_size = 0
        max_bytes = settings.MAX_VIDEO_FILE_SIZE_BYTES
        try:
            with open(destination_path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Uploaded file exceeds maximum allowed size of {max_bytes // (1024 * 1024)}MB.",
                        )
                    buffer.write(chunk)
        except Exception as e:
            if os.path.exists(destination_path):
                os.remove(destination_path)
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Failed to stream uploaded video to disk: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded video file.",
            )

        if total_size == 0:
            if os.path.exists(destination_path):
                os.remove(destination_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded video file is empty (0 bytes).",
            )

        # 5. Inspect video with OpenCV
        try:
            metadata = SnapshotExtractor.inspect_video(destination_path)
        except VideoProcessingError as vpe:
            if os.path.exists(destination_path):
                os.remove(destination_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video validation failed: {str(vpe)}",
            )
        except Exception as e:
            if os.path.exists(destination_path):
                os.remove(destination_path)
            logger.error(f"Unexpected OpenCV error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid playable MP4 video.",
            )

        # 6. Clean up prior video file for this session if one existed
        if session.video_file_path and os.path.exists(session.video_file_path) and session.video_file_path != destination_path:
            try:
                os.remove(session.video_file_path)
            except Exception as e:
                logger.warning(f"Could not remove old video file {session.video_file_path}: {e}")

        # 7. Update MonitoringSession record in DB
        session.video_file_path = destination_path
        session.video_filename = orig_filename
        session.video_file_size = total_size
        session.video_width = metadata["width"]
        session.video_height = metadata["height"]
        session.video_fps = metadata["fps"]
        session.video_total_frames = metadata["total_frames"]
        session.video_duration_seconds = metadata["duration_seconds"]
        session.video_processing_status = "NOT_STARTED"
        session.video_error_message = None

        db.commit()
        db.refresh(session)

        return VideoUploadResponse(
            session_id=session.id,
            video_filename=orig_filename,
            file_size=total_size,
            duration_seconds=metadata["duration_seconds"],
            fps=metadata["fps"],
            width=metadata["width"],
            height=metadata["height"],
            total_frames=metadata["total_frames"],
            video_processing_status="NOT_STARTED",
            message="Video uploaded and validated successfully.",
        )

    @classmethod
    def extract_snapshots_for_session(
        cls,
        session: MonitoringSession,
        interval_seconds: Optional[int],
        max_snapshots: Optional[int],
        db: Session,
    ) -> VideoProcessResponse:
        """Executes periodic frame extraction via OpenCV and registers Snapshot records."""
        # Auto-resolve video path if directory was moved or renamed
        video_path = session.video_file_path
        if not video_path or not os.path.exists(video_path):
            session_video_dir = cls.get_video_dir_for_session(session.id)
            if video_path:
                candidate = os.path.join(session_video_dir, os.path.basename(video_path))
                if os.path.exists(candidate):
                    video_path = candidate
                    session.video_file_path = candidate
                    db.commit()
            if not video_path or not os.path.exists(video_path):
                if os.path.exists(session_video_dir):
                    for fname in sorted(os.listdir(session_video_dir)):
                        if fname.endswith(".mp4"):
                            candidate = os.path.join(session_video_dir, fname)
                            if os.path.getsize(candidate) > 0:
                                video_path = candidate
                                session.video_file_path = candidate
                                db.commit()
                                break

        if not video_path or not os.path.exists(video_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No uploaded video file found for this session. Please upload an MP4 video first.",
            )

        # Determine interval and max snapshots
        effective_interval = interval_seconds or settings.SNAPSHOT_INTERVAL_SECONDS
        effective_max = max_snapshots or settings.MAX_SNAPSHOTS_PER_SESSION

        # Mark session video processing status as PROCESSING
        session.video_processing_status = "PROCESSING"
        session.video_error_message = None
        db.commit()

        snapshot_dir = cls.get_snapshot_dir_for_session(session.id)
        extractor = SnapshotExtractor(
            interval_seconds=effective_interval,
            max_snapshots=effective_max,
            jpeg_quality=settings.JPEG_QUALITY,
        )

        try:
            extracted_frames = extractor.extract_periodic_snapshots(
                video_path=video_path,
                output_dir=snapshot_dir,
            )

            # Clear previous snapshots for this session if re-extracting
            db.query(Snapshot).filter(Snapshot.monitoring_session_id == session.id).delete()

            # Persist new Snapshot records
            saved_snapshots: List[Snapshot] = []
            for frame_info in extracted_frames:
                snapshot_record = Snapshot(
                    monitoring_session_id=session.id,
                    file_path=frame_info["file_path"],
                    sequence_number=frame_info["sequence_number"],
                    frame_time_seconds=frame_info["frame_time_seconds"],
                    width=frame_info["width"],
                    height=frame_info["height"],
                    processing_status="PENDING",  # Awaiting future AI modules
                )
                db.add(snapshot_record)
                saved_snapshots.append(snapshot_record)

            session.video_processing_status = "COMPLETED"
            db.commit()

            # Refresh records
            for s in saved_snapshots:
                db.refresh(s)

            response_snapshots = [
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
                for s in saved_snapshots
            ]

            return VideoProcessResponse(
                session_id=session.id,
                snapshots_created=len(saved_snapshots),
                duration_seconds=session.video_duration_seconds or 0.0,
                interval_seconds=effective_interval,
                video_processing_status="COMPLETED",
                message=f"Extracted {len(saved_snapshots)} snapshots successfully.",
                snapshots=response_snapshots,
            )

        except VideoProcessingError as vpe:
            db.rollback()
            session.video_processing_status = "FAILED"
            session.video_error_message = str(vpe)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Snapshot extraction failed: {str(vpe)}",
            )
        except Exception as e:
            db.rollback()
            session.video_processing_status = "FAILED"
            session.video_error_message = str(e)
            db.commit()
            logger.error(f"Unexpected error during snapshot extraction: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during video frame extraction.",
            )

    @classmethod
    def get_secure_snapshot_path(
        cls,
        snapshot_id: int,
        current_user: User,
        db: Session,
    ) -> str:
        """Resolves snapshot image path and strictly enforces authorization and path traversal checks."""
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot with id {snapshot_id} not found.",
            )

        # Scoped authorization check for CENTRE_USER
        session = snapshot.monitoring_session
        if current_user.role == "CENTRE_USER" and current_user.centre_id:
            if session.centre_id != current_user.centre_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You do not have permission to view snapshots from this centre.",
                )

        file_path = os.path.abspath(snapshot.file_path)
        storage_root = cls._get_storage_root()

        # If file does not exist at stored path, check if it exists in current storage root
        if not os.path.exists(file_path):
            candidate = os.path.join(
                storage_root,
                settings.SNAPSHOT_DIR,
                f"session_{snapshot.monitoring_session_id}",
                os.path.basename(snapshot.file_path),
            )
            if os.path.exists(candidate):
                file_path = os.path.abspath(candidate)
                snapshot.file_path = file_path
                db.commit()

        # Prevent path traversal outside storage root
        try:
            common = os.path.commonpath([storage_root, file_path])
            if common != storage_root:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Invalid storage path.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Path traversal detected.",
            )

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot file does not exist on storage.",
            )

        return file_path
