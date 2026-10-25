"""Attendance AI Business Service.

Coordinates YOLO26 inference, observation persistence, evidence generation,
and session-level aggregation workflows.
"""

import os
import json
import logging
from typing import List, Optional
import cv2
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.attendance import AttendanceObservation
from backend.app.pipelines.attendance.loader import get_attendance_detector
from backend.app.pipelines.attendance.base import AttendanceDetectionResult

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service handling attendance inference and observation persistence."""

    @staticmethod
    def detect_snapshot_attendance(
        snapshot_id: int,
        db: Session,
        current_user: User,
        confidence_threshold: Optional[float] = None,
    ) -> AttendanceObservation:
        """Runs YOLO26 attendance presence detection on a single snapshot.
        
        Enforces idempotency: updates existing observation if already processed.
        """
        # 1. Fetch snapshot
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot with ID {snapshot_id} not found.",
            )

        # 2. Verify image file exists
        full_image_path = snapshot.file_path if (snapshot.file_path and os.path.isabs(snapshot.file_path)) else os.path.join(settings.STORAGE_ROOT, snapshot.file_path)
        if not os.path.exists(full_image_path):
            candidate = os.path.join(
                os.path.abspath(settings.STORAGE_ROOT),
                settings.SNAPSHOT_DIR,
                f"session_{snapshot.monitoring_session_id}",
                os.path.basename(snapshot.file_path),
            )
            if os.path.exists(candidate):
                full_image_path = candidate
                snapshot.file_path = candidate
                db.commit()

        if not os.path.exists(full_image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot image file not found on disk at {snapshot.file_path}.",
            )

        # 3. Obtain detector and check availability
        detector = get_attendance_detector()
        if not detector.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Attendance AI model '{detector.model_name}' is not configured. "
                    f"Weights missing at '{detector.model_path}'. "
                    "Please configure model weights before initiating detection."
                ),
            )

        # 4. Execute presence detection
        result: AttendanceDetectionResult = detector.detect(
            image=full_image_path,
            confidence_threshold=confidence_threshold,
            render_annotated=settings.ATTENDANCE_SAVE_ANNOTATED,
        )

        if result.status == "WEIGHTS_MISSING":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.error_message or "Attendance AI model is not configured.",
            )
        elif result.status == "ERROR":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message or "Inference engine encountered an internal error.",
            )

        # 5. Save annotated image evidence if generated
        annotated_rel_path = None
        if result.annotated_image is not None and settings.ATTENDANCE_SAVE_ANNOTATED:
            try:
                evidence_dir = os.path.join(
                    settings.STORAGE_ROOT,
                    settings.EVIDENCE_DIR,
                    f"session_{snapshot.monitoring_session_id}",
                )
                os.makedirs(evidence_dir, exist_ok=True)
                evidence_filename = f"annotated_snap_{snapshot.sequence_number:06d}.jpg"
                evidence_full_path = os.path.join(evidence_dir, evidence_filename)
                cv2.imwrite(
                    evidence_full_path,
                    result.annotated_image,
                    [int(cv2.IMWRITE_JPEG_QUALITY), settings.JPEG_QUALITY],
                )
                annotated_rel_path = os.path.relpath(evidence_full_path, settings.STORAGE_ROOT)
            except Exception as e:
                logger.warning(f"Failed to save annotated evidence image: {e}")

        # 6. Serialize generic detection metadata (boxes and confidences, zero identities)
        detections_json = json.dumps([
            {
                "bbox": d.bbox,
                "confidence": d.confidence,
                "class_name": d.class_name,
            }
            for d in result.detections
        ])

        # 7. Idempotent database record update or creation
        observation = (
            db.query(AttendanceObservation)
            .filter(AttendanceObservation.snapshot_id == snapshot.id)
            .first()
        )

        if observation:
            # Update existing observation
            observation.monitoring_session_id = snapshot.monitoring_session_id
            observation.observed_count = result.detected_count
            observation.confidence_score = result.avg_confidence
            observation.min_confidence = result.min_confidence
            observation.max_confidence = result.max_confidence
            observation.confidence_threshold = result.confidence_threshold
            observation.model_name = result.model_name
            observation.model_version = result.model_version
            observation.inference_time_ms = result.inference_time_ms
            observation.inference_device = result.inference_device
            observation.processing_status = "COMPLETED"
            if annotated_rel_path:
                observation.annotated_image_path = annotated_rel_path
            observation.detection_metadata = detections_json
        else:
            # Create new observation
            observation = AttendanceObservation(
                snapshot_id=snapshot.id,
                monitoring_session_id=snapshot.monitoring_session_id,
                observed_count=result.detected_count,
                confidence_score=result.avg_confidence,
                min_confidence=result.min_confidence,
                max_confidence=result.max_confidence,
                confidence_threshold=result.confidence_threshold,
                model_name=result.model_name,
                model_version=result.model_version,
                inference_time_ms=result.inference_time_ms,
                inference_device=result.inference_device,
                processing_status="COMPLETED",
                annotated_image_path=annotated_rel_path,
                detection_metadata=detections_json,
            )
            db.add(observation)

        # Update snapshot status
        snapshot.processing_status = "COMPLETED"
        db.commit()
        db.refresh(observation)
        return observation

    @staticmethod
    def process_session_attendance(
        session_id: int,
        db: Session,
        current_user: User,
        confidence_threshold: Optional[float] = None,
    ) -> dict:
        """Processes all snapshots for a given session through YOLO26 presence detection."""
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring session with ID {session_id} not found.",
            )

        snapshots = (
            db.query(Snapshot)
            .filter(Snapshot.monitoring_session_id == session_id)
            .order_by(Snapshot.sequence_number.asc())
            .all()
        )

        if not snapshots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No snapshots found for session #{session_id}. Please upload a video and extract snapshots first.",
            )

        detector = get_attendance_detector()
        if not detector.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Attendance AI model '{detector.model_name}' is not configured. "
                    f"Weights missing at '{detector.model_path}'."
                ),
            )

        processed_count = 0
        for snap in snapshots:
            try:
                AttendanceService.detect_snapshot_attendance(
                    snapshot_id=snap.id,
                    db=db,
                    current_user=current_user,
                    confidence_threshold=confidence_threshold,
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process attendance on snapshot #{snap.id}: {e}")

        return {
            "session_id": session_id,
            "snapshots_processed": processed_count,
            "observations_created": processed_count,
            "model_name": detector.model_name,
            "model_version": detector.model_version,
            "status": "COMPLETED",
            "message": f"Successfully processed {processed_count} snapshots through YOLO26 attendance detector.",
        }

    @staticmethod
    def get_session_observations(
        session_id: int,
        db: Session,
        current_user: User,
    ) -> List[AttendanceObservation]:
        """Retrieves all attendance observations recorded for a session."""
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring session with ID {session_id} not found.",
            )

        return (
            db.query(AttendanceObservation)
            .filter(AttendanceObservation.monitoring_session_id == session_id)
            .join(Snapshot, Snapshot.id == AttendanceObservation.snapshot_id)
            .order_by(Snapshot.sequence_number.asc())
            .all()
        )

    @staticmethod
    def get_secure_annotated_path(
        observation_id: int,
        current_user: User,
        db: Session,
    ) -> str:
        """Validates authorization and path traversal before returning annotated evidence image path."""
        observation = db.query(AttendanceObservation).filter(AttendanceObservation.id == observation_id).first()
        if not observation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attendance observation #{observation_id} not found.",
            )

        if not observation.annotated_image_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No annotated evidence image available for this observation.",
            )

        root_abs = os.path.abspath(settings.STORAGE_ROOT)
        target_abs = os.path.abspath(os.path.join(root_abs, observation.annotated_image_path))

        # Path traversal defense
        try:
            common = os.path.commonpath([root_abs, target_abs])
            if common != root_abs:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: invalid file path.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: path traversal attempt detected.",
            )

        if not os.path.exists(target_abs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotated image file not found on disk.",
            )

        return target_abs
