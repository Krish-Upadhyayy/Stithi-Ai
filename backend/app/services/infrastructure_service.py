"""Infrastructure AI Business Service.

Coordinates YOLO26 infrastructure asset detection, observation persistence,
inventory mapping, visual evidence generation, and session-level aggregation workflows.
Strict Constraint (Prompt 11):
- Records apparent visible presence and counts only.
- Never claims equipment is mechanically/electrically functional.
- Decoupled entirely from Attendance AI.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import cv2
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.session import MonitoringSession
from backend.app.models.snapshot import Snapshot
from backend.app.models.infrastructure import InfrastructureObservation
from backend.app.models.inventory import InventoryItem
from backend.app.pipelines.infrastructure.loader import get_infrastructure_detector
from backend.app.pipelines.infrastructure.mapping import default_mapper
from backend.app.pipelines.infrastructure.base import InfrastructureDetectionResult

logger = logging.getLogger(__name__)


class InfrastructureService:
    """Service handling infrastructure detection and observation persistence."""

    @staticmethod
    def detect_snapshot_infrastructure(
        snapshot_id: int,
        db: Session,
        current_user: User,
        confidence_threshold: Optional[float] = None,
        render_annotated: bool = True,
    ) -> Dict[str, Any]:
        """Runs YOLO26 infrastructure detection on a single snapshot and records observations.
        
        Enforces idempotency: replaces prior observations for this snapshot to prevent duplicates.
        """
        # 1. Fetch snapshot
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot with ID {snapshot_id} not found.",
            )

        # 2. Verify image file exists on disk
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
        detector = get_infrastructure_detector()
        if not detector.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Infrastructure AI model is not configured. "
                    f"Weights missing at '{detector.model_path}'. "
                    "Please configure model weights before initiating detection."
                ),
            )

        # 4. Fetch session and centre inventory items for mapping
        session = db.query(MonitoringSession).filter(MonitoringSession.id == snapshot.monitoring_session_id).first()
        inventory_items = []
        if session:
            inventory_items = db.query(InventoryItem).filter(InventoryItem.centre_id == session.centre_id).all()

        # Build lookup: normalized AI class -> InventoryItem
        class_to_inventory_item: Dict[str, InventoryItem] = {}
        for inv_item in inventory_items:
            mapped_cls = default_mapper.map_inventory_to_class(inv_item.item_name)
            if mapped_cls and mapped_cls not in class_to_inventory_item:
                class_to_inventory_item[mapped_cls.lower()] = inv_item

        # 5. Execute infrastructure detection
        conf_thresh = confidence_threshold or settings.INFRASTRUCTURE_CONFIDENCE_THRESHOLD
        result: InfrastructureDetectionResult = detector.detect(
            image=full_image_path,
            confidence_threshold=conf_thresh,
            render_annotated=render_annotated and settings.INFRASTRUCTURE_SAVE_ANNOTATED,
        )

        if result.status == "WEIGHTS_MISSING":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.error_message or "Infrastructure AI model is not configured.",
            )
        elif result.status == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message or "Inference engine encountered an internal error.",
            )

        # 6. Save annotated evidence image if rendered
        annotated_rel_path = None
        if result.annotated_image is not None and settings.INFRASTRUCTURE_SAVE_ANNOTATED:
            try:
                evidence_dir = os.path.join(
                    settings.STORAGE_ROOT,
                    settings.EVIDENCE_DIR,
                    "infrastructure",
                    f"session_{snapshot.monitoring_session_id}",
                )
                os.makedirs(evidence_dir, exist_ok=True)
                evidence_filename = f"annotated_infra_snap_{snapshot.sequence_number:06d}.jpg"
                evidence_full_path = os.path.join(evidence_dir, evidence_filename)
                cv2.imwrite(
                    evidence_full_path,
                    result.annotated_image,
                    [int(cv2.IMWRITE_JPEG_QUALITY), settings.JPEG_QUALITY],
                )
                annotated_rel_path = os.path.relpath(evidence_full_path, settings.STORAGE_ROOT)
            except Exception as e:
                logger.warning(f"Failed to save annotated infrastructure evidence: {e}")

        # 7. Idempotent database record update: clear prior observations for this snapshot
        db.query(InfrastructureObservation).filter(
            InfrastructureObservation.snapshot_id == snapshot.id
        ).delete(synchronize_session=False)

        observations: List[InfrastructureObservation] = []
        detection_summaries = []

        # Create observation for each detected asset class
        for cls_name, count in result.class_counts.items():
            stats = result.get_class_confidence_stats(cls_name)
            inv_item = class_to_inventory_item.get(cls_name.lower())

            # Collect matching bounding boxes
            boxes_for_class = [
                {
                    "bbox": d.bbox,
                    "confidence": d.confidence,
                    "class_name": d.class_name,
                }
                for d in result.detections
                if d.class_name.lower() == cls_name.lower()
            ]

            obs = InfrastructureObservation(
                snapshot_id=snapshot.id,
                monitoring_session_id=snapshot.monitoring_session_id,
                inventory_item_id=inv_item.id if inv_item else None,
                asset_type=cls_name,
                detected_quantity=count,
                confidence=stats["avg"],
                min_confidence=stats["min"],
                max_confidence=stats["max"],
                confidence_threshold=conf_thresh,
                model_name=result.model_name,
                model_version=result.model_version,
                inference_time_ms=result.inference_time_ms,
                inference_device=result.inference_device,
                processing_status="COMPLETED",
                annotated_image_path=annotated_rel_path,
                bounding_boxes=json.dumps(boxes_for_class),
            )
            db.add(obs)
            observations.append(obs)

            detection_summaries.append({
                "asset_type": cls_name,
                "detected_class": cls_name,
                "count": count,
                "detected_count": count,
                "confidence": stats["avg"],
                "min_confidence": stats["min"],
                "max_confidence": stats["max"],
                "status": "Visually detected",
                "mapped_inventory_item": inv_item.item_name if inv_item else None,
            })

        db.commit()
        for o in observations:
            db.refresh(o)

        return {
            "snapshot_id": snapshot.id,
            "monitoring_session_id": snapshot.monitoring_session_id,
            "detections": detection_summaries,
            "observations": observations,
            "total_detected_assets": result.total_detected_assets,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "inference_time_ms": result.inference_time_ms,
            "status": "SUCCESS",
            "message": f"Successfully detected {result.total_detected_assets} assets across {len(result.class_counts)} classes.",
            "has_annotated_image": annotated_rel_path is not None,
        }

    @staticmethod
    def process_session_infrastructure(
        session_id: int,
        db: Session,
        current_user: User,
        confidence_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Batch processes all snapshots in a monitoring session through YOLO26 Infrastructure AI."""
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring session with ID {session_id} not found.",
            )

        detector = get_infrastructure_detector()
        if not detector.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Infrastructure AI model is not configured. Weights missing.",
            )

        snapshots = (
            db.query(Snapshot)
            .filter(Snapshot.monitoring_session_id == session_id)
            .order_by(Snapshot.sequence_number.asc())
            .all()
        )

        if not snapshots:
            return {
                "session_id": session_id,
                "snapshots_processed": 0,
                "observations_created": 0,
                "detected_summary": {},
                "model_name": detector.model_name,
                "model_version": detector.model_version,
                "status": "COMPLETED",
                "message": "No snapshots available for infrastructure processing.",
            }

        total_observations_created = 0
        overall_detected_summary: Dict[str, int] = {}

        for snap in snapshots:
            try:
                res = InfrastructureService.detect_snapshot_infrastructure(
                    snapshot_id=snap.id,
                    db=db,
                    current_user=current_user,
                    confidence_threshold=confidence_threshold,
                    render_annotated=True,
                )
                total_observations_created += len(res.get("observations", []))
                for det in res.get("detections", []):
                    cls_k = det["asset_type"]
                    overall_detected_summary[cls_k] = max(
                        overall_detected_summary.get(cls_k, 0),
                        det["count"],
                    )
            except Exception as e:
                logger.error(f"Error processing infrastructure for snapshot {snap.id}: {e}")

        return {
            "session_id": session_id,
            "snapshots_processed": len(snapshots),
            "observations_created": total_observations_created,
            "detected_summary": overall_detected_summary,
            "model_name": detector.model_name,
            "model_version": detector.model_version,
            "status": "COMPLETED",
            "message": f"Successfully processed {len(snapshots)} snapshots for session {session_id}.",
        }

    @staticmethod
    def get_session_observations(
        session_id: int,
        db: Session,
        current_user: User,
    ) -> List[InfrastructureObservation]:
        """Retrieves all infrastructure observations recorded for a monitoring session."""
        session = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring session with ID {session_id} not found.",
            )

        return (
            db.query(InfrastructureObservation)
            .filter(InfrastructureObservation.monitoring_session_id == session_id)
            .order_by(InfrastructureObservation.created_at.asc())
            .all()
        )

    @staticmethod
    def get_secure_annotated_path(
        observation_id: int,
        current_user: User,
        db: Session,
    ) -> str:
        """Resolves secure filesystem path to annotated infrastructure evidence with path traversal protection."""
        obs = db.query(InfrastructureObservation).filter(InfrastructureObservation.id == observation_id).first()
        if not obs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infrastructure observation with ID {observation_id} not found.",
            )

        if not obs.annotated_image_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No annotated evidence image recorded for this observation.",
            )

        full_path = os.path.abspath(os.path.join(settings.STORAGE_ROOT, obs.annotated_image_path))
        base_storage = os.path.abspath(settings.STORAGE_ROOT)
        if not full_path.startswith(base_storage):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: Invalid evidence file path.",
            )

        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence image file not found on disk.",
            )

        return full_path
