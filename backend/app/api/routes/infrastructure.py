"""Infrastructure AI detection and observation endpoints using YOLO26.

Strict Constraint (Prompt 11):
- Records apparent visual presence and counts of sanctioned infrastructure assets only.
- Never claims equipment is mechanically/electrically functional based on CCTV frames.
- Decoupled completely from Attendance AI.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.services.infrastructure_service import InfrastructureService
from backend.app.schemas.infrastructure import (
    ProcessSnapshotInfrastructureRequest,
    ProcessSessionInfrastructureRequest,
    SnapshotInfrastructureResponse,
    ProcessSessionInfrastructureResponse,
    InfrastructureObservationResponse,
    DetectedAssetSummary,
)
from backend.app.pipelines.infrastructure.loader import get_infrastructure_detector

router = APIRouter(tags=["Infrastructure AI (YOLO26)"])


@router.post(
    "/monitoring/snapshots/{snapshot_id}/infrastructure",
    response_model=SnapshotInfrastructureResponse,
    summary="Run YOLO26 infrastructure asset detection on a single snapshot",
)
def detect_snapshot_infrastructure(
    snapshot_id: int,
    request_data: Optional[ProcessSnapshotInfrastructureRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes YOLO26 infrastructure asset detection on a single snapshot and records observations.
    
    Idempotent: updates/replaces existing observations for this snapshot to prevent duplicates.
    """
    conf_thresh = request_data.confidence_threshold if request_data else None
    render_annotated = request_data.render_annotated if request_data else True

    result = InfrastructureService.detect_snapshot_infrastructure(
        snapshot_id=snapshot_id,
        db=db,
        current_user=current_user,
        confidence_threshold=conf_thresh,
        render_annotated=render_annotated,
    )

    observation_responses = [
        InfrastructureObservationResponse(
            id=obs.id,
            snapshot_id=obs.snapshot_id,
            monitoring_session_id=obs.monitoring_session_id,
            inventory_item_id=obs.inventory_item_id,
            asset_type=obs.asset_type,
            detected_quantity=obs.detected_quantity,
            detected_class=obs.asset_type,
            detected_count=obs.detected_quantity,
            confidence=obs.confidence,
            min_confidence=obs.min_confidence,
            max_confidence=obs.max_confidence,
            confidence_threshold=obs.confidence_threshold,
            model_name=obs.model_name,
            model_version=obs.model_version,
            inference_time_ms=obs.inference_time_ms,
            inference_device=obs.inference_device,
            processing_status=obs.processing_status,
            has_annotated_image=bool(obs.annotated_image_path),
            apparent_condition="Visually detected",
            created_at=obs.created_at,
        )
        for obs in result["observations"]
    ]

    detection_summaries = [
        DetectedAssetSummary(
            asset_type=d["asset_type"],
            detected_class=d["detected_class"],
            count=d["count"],
            detected_count=d["detected_count"],
            confidence=d["confidence"],
            min_confidence=d["min_confidence"],
            max_confidence=d["max_confidence"],
            status=d["status"],
            mapped_inventory_item=d["mapped_inventory_item"],
        )
        for d in result["detections"]
    ]

    return SnapshotInfrastructureResponse(
        snapshot_id=result["snapshot_id"],
        monitoring_session_id=result["monitoring_session_id"],
        detections=detection_summaries,
        observations=observation_responses,
        total_detected_assets=result["total_detected_assets"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        inference_time_ms=result["inference_time_ms"],
        status=result["status"],
        message=result["message"],
        has_annotated_image=result["has_annotated_image"],
    )


@router.post(
    "/monitoring/sessions/{session_id}/infrastructure/process",
    response_model=ProcessSessionInfrastructureResponse,
    summary="Batch process all session snapshots through YOLO26 infrastructure detector",
)
def process_session_infrastructure(
    session_id: int,
    request_data: Optional[ProcessSessionInfrastructureRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch processes all extracted snapshots for a monitoring session through YOLO26."""
    conf_thresh = request_data.confidence_threshold if request_data else None
    result = InfrastructureService.process_session_infrastructure(
        session_id=session_id,
        db=db,
        current_user=current_user,
        confidence_threshold=conf_thresh,
    )

    return ProcessSessionInfrastructureResponse(
        session_id=result["session_id"],
        snapshots_processed=result["snapshots_processed"],
        observations_created=result["observations_created"],
        detected_summary=result["detected_summary"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        status=result["status"],
        message=result["message"],
    )


@router.get(
    "/monitoring/sessions/{session_id}/infrastructure/observations",
    response_model=List[InfrastructureObservationResponse],
    summary="Retrieve all infrastructure observations recorded for a monitoring session",
)
def get_session_infrastructure_observations(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all infrastructure observations recorded for a session."""
    observations = InfrastructureService.get_session_observations(
        session_id=session_id,
        db=db,
        current_user=current_user,
    )
    return [
        InfrastructureObservationResponse(
            id=obs.id,
            snapshot_id=obs.snapshot_id,
            monitoring_session_id=obs.monitoring_session_id,
            inventory_item_id=obs.inventory_item_id,
            asset_type=obs.asset_type,
            detected_quantity=obs.detected_quantity,
            detected_class=obs.asset_type,
            detected_count=obs.detected_quantity,
            confidence=obs.confidence,
            min_confidence=obs.min_confidence,
            max_confidence=obs.max_confidence,
            confidence_threshold=obs.confidence_threshold,
            model_name=obs.model_name,
            model_version=obs.model_version,
            inference_time_ms=obs.inference_time_ms,
            inference_device=obs.inference_device,
            processing_status=obs.processing_status,
            has_annotated_image=bool(obs.annotated_image_path),
            apparent_condition="Visually detected",
            created_at=obs.created_at,
        )
        for obs in observations
    ]


@router.get(
    "/monitoring/infrastructure/observations/{observation_id}/annotated",
    summary="Securely stream annotated infrastructure evidence snapshot image",
)
def get_annotated_infrastructure_image(
    observation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely streams annotated evidence snapshot showing infrastructure bounding boxes."""
    file_path = InfrastructureService.get_secure_annotated_path(
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
    "/ai/infrastructure/model-info",
    summary="Retrieve active infrastructure model configuration and availability",
)
def get_infrastructure_model_info():
    """Retrieves deployment state of the infrastructure detector."""
    detector = get_infrastructure_detector()
    return {
        "model_name": getattr(detector, "model_name", "YOLO26-Infrastructure"),
        "model_version": getattr(detector, "model_version", "v1-baseline"),
        "is_available": detector.is_available(),
        "weights_path": getattr(detector, "model_path", None),
        "device": getattr(detector, "device", "cpu"),
        "confidence_threshold": getattr(detector, "confidence_threshold", 0.40),
        "target_classes": getattr(detector, "target_classes", []),
    }
