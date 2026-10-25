"""Attendance AI detection and observation endpoints using YOLO26.

Strict Privacy Constraint (SRS §FR-03 & PRD §9):
- Anonymous aggregate presence and headcount counting only.
- Zero face recognition or biometric identification.
- Answers: 'How many people appear to be present in this snapshot?'
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.attendance import AttendanceObservation
from backend.app.services.attendance_service import AttendanceService
from backend.app.schemas.attendance import (
    ProcessSnapshotAttendanceRequest,
    ProcessSessionAttendanceRequest,
    AttendanceObservationResponse,
    ProcessSessionAttendanceResponse,
)

router = APIRouter(tags=["Attendance AI (YOLO26)"])


@router.post(
    "/monitoring/snapshots/{snapshot_id}/attendance",
    response_model=AttendanceObservationResponse,
    summary="Run YOLO26 attendance presence detection on a single snapshot",
)
def detect_snapshot_attendance(
    snapshot_id: int,
    request_data: Optional[ProcessSnapshotAttendanceRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes YOLO26 presence detection on a snapshot and records an AttendanceObservation.
    
    Strictly anonymous headcount. Zero student identities recorded.
    """
    conf_thresh = request_data.confidence_threshold if request_data else None
    observation = AttendanceService.detect_snapshot_attendance(
        snapshot_id=snapshot_id,
        db=db,
        current_user=current_user,
        confidence_threshold=conf_thresh,
    )
    return AttendanceObservationResponse(
        id=observation.id,
        snapshot_id=observation.snapshot_id,
        monitoring_session_id=observation.monitoring_session_id,
        observed_count=observation.observed_count,
        detected_count=observation.observed_count,
        confidence_score=observation.confidence_score,
        min_confidence=observation.min_confidence,
        max_confidence=observation.max_confidence,
        confidence_threshold=observation.confidence_threshold,
        model_name=observation.model_name,
        model_version=observation.model_version,
        inference_time_ms=observation.inference_time_ms,
        inference_device=observation.inference_device,
        processing_status=observation.processing_status,
        has_annotated_image=bool(observation.annotated_image_path),
        created_at=observation.created_at,
    )


@router.post(
    "/monitoring/sessions/{session_id}/attendance/process",
    response_model=ProcessSessionAttendanceResponse,
    summary="Process all session snapshots through YOLO26 attendance detector",
)
def process_session_attendance(
    session_id: int,
    request_data: Optional[ProcessSessionAttendanceRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch processes all extracted snapshots for a session through the YOLO26 presence detector."""
    conf_thresh = request_data.confidence_threshold if request_data else None
    result = AttendanceService.process_session_attendance(
        session_id=session_id,
        db=db,
        current_user=current_user,
        confidence_threshold=conf_thresh,
    )
    return ProcessSessionAttendanceResponse(
        session_id=result["session_id"],
        snapshots_processed=result["snapshots_processed"],
        observations_created=result["observations_created"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        status=result["status"],
        message=result["message"],
    )


@router.get(
    "/monitoring/sessions/{session_id}/attendance/observations",
    response_model=List[AttendanceObservationResponse],
    summary="Retrieve all attendance observations recorded for a session",
)
def get_session_attendance_observations(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all chronological attendance observations recorded for a session."""
    observations = AttendanceService.get_session_observations(
        session_id=session_id,
        db=db,
        current_user=current_user,
    )
    return [
        AttendanceObservationResponse(
            id=obs.id,
            snapshot_id=obs.snapshot_id,
            monitoring_session_id=obs.monitoring_session_id,
            observed_count=obs.observed_count,
            detected_count=obs.observed_count,
            confidence_score=obs.confidence_score,
            min_confidence=obs.min_confidence,
            max_confidence=obs.max_confidence,
            confidence_threshold=obs.confidence_threshold,
            model_name=obs.model_name,
            model_version=obs.model_version,
            inference_time_ms=obs.inference_time_ms,
            inference_device=obs.inference_device,
            processing_status=obs.processing_status,
            has_annotated_image=bool(obs.annotated_image_path),
            created_at=obs.created_at,
        )
        for obs in observations
    ]


@router.get(
    "/monitoring/attendance/observations/{observation_id}/annotated",
    summary="Securely stream annotated evidence snapshot image",
)
def get_annotated_observation_image(
    observation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely streams annotated evidence snapshot image showing bounding box detections."""
    file_path = AttendanceService.get_secure_annotated_path(
        observation_id=observation_id,
        current_user=current_user,
        db=db,
    )
    return FileResponse(
        path=file_path,
        media_type="image/jpeg",
        filename=os.path.basename(file_path),
    )


@router.get(
    "/ai/attendance/evaluation",
    summary="Retrieve empirical evaluation metrics for the active attendance model",
)
def get_attendance_evaluation():
    """Retrieves verified evaluation results from empirical benchmarks.
    
    Zero fabricated numbers. Returns 'NOT_EVALUATED' if benchmarks have not yet been executed.
    """
    import json
    from backend.app.ml.attendance.registry import AttendanceModelRegistry

    # 1. Check production metadata
    prod = AttendanceModelRegistry.get_production_metadata()
    if prod and "metrics" in prod:
        return {
            "status": "EVALUATED",
            "model_name": prod.get("model_name"),
            "model_version": prod.get("version"),
            "dataset_version": prod.get("dataset_version"),
            "registered_at": prod.get("registered_at"),
            "selection_rationale": prod.get("selection_rationale"),
            "metrics": prod.get("metrics"),
        }

    # 2. Check baseline evaluation report
    baseline_path = "models/attendance/baseline/evaluation_metrics.json"
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "status": "EVALUATED",
                "model_name": data.get("model_name", "YOLO26-Baseline"),
                "model_version": data.get("model_version", "v1-baseline"),
                "evaluation_date": data.get("evaluation_date"),
                "metrics": data,
            }
        except Exception:
            pass

    return {
        "status": "NOT_EVALUATED",
        "message": "Evaluation results are not available yet. Run scripts/attendance/evaluate_baseline.py with a verified dataset to generate empirical benchmark metrics.",
    }


@router.get(
    "/ai/attendance/model-info",
    summary="Retrieve active attendance model status and registry metadata",
)
def get_attendance_model_info():
    """Retrieves deployment state of the attendance model."""
    from backend.app.pipelines.attendance.loader import get_attendance_detector
    from backend.app.ml.attendance.registry import AttendanceModelRegistry

    detector = get_attendance_detector()
    prod_meta = AttendanceModelRegistry.get_production_metadata()

    return {
        "model_name": getattr(detector, "model_name", "YOLO26-Face-Presence"),
        "model_version": getattr(detector, "model_version", "v1-baseline"),
        "is_available": detector.is_available(),
        "weights_path": getattr(detector, "model_path", None),
        "is_production_registered": prod_meta is not None,
        "device": getattr(detector, "device", "cpu"),
        "confidence_threshold": getattr(detector, "confidence_threshold", 0.40),
        "production_metadata": prod_meta,
    }

