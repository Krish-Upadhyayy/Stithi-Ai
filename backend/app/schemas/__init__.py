"""Pydantic schemas package exports."""

from backend.app.schemas.health import HealthStatus
from backend.app.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from backend.app.schemas.centre import CentreCreate, CentreResponse, CentreUpdate, CentreStatusUpdate
from backend.app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate, CameraStatusUpdate
from backend.app.schemas.session import (
    MonitoringSessionCreate,
    MonitoringSessionResponse,
    MonitoringSessionDetailResponse,
)
from backend.app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryRowError,
    InventoryParsedItem,
    InventoryUploadPreviewResponse,
    InventoryConfirmRequest,
    InventoryConfirmResponse,
)
from backend.app.schemas.snapshot import (
    SnapshotResponse,
    VideoUploadResponse,
    VideoProcessRequest,
    VideoProcessResponse,
)
from backend.app.schemas.alert import (
    AlertResponse,
    AlertStatusUpdate,
    AlertEvidenceResponse,
    AlertReviewRequest,
    AlertGenerationResponse,
    AlertSummaryResponse,
)
from backend.app.schemas.attendance import (
    DetectionBoxSchema,
    ProcessSnapshotAttendanceRequest,
    ProcessSessionAttendanceRequest,
    AttendanceObservationResponse,
    ProcessSessionAttendanceResponse,
)
from backend.app.schemas.infrastructure import (
    DetectedAssetSummary,
    ProcessSnapshotInfrastructureRequest,
    ProcessSessionInfrastructureRequest,
    InfrastructureObservationResponse,
    SnapshotInfrastructureResponse,
    ProcessSessionInfrastructureResponse,
)
from backend.app.schemas.compliance import (
    AttendanceComplianceSchema,
    InfrastructureComplianceItemSchema,
    CalculateComplianceRequest,
    SessionComplianceResponse,
    ComplianceDashboardSummaryResponse,
)

__all__ = [
    "HealthStatus",
    "UserCreate",
    "UserResponse",
    "LoginRequest",
    "TokenResponse",
    "CentreCreate",
    "CentreUpdate",
    "CentreStatusUpdate",
    "CentreResponse",
    "CameraCreate",
    "CameraUpdate",
    "CameraStatusUpdate",
    "CameraResponse",
    "MonitoringSessionCreate",
    "MonitoringSessionResponse",
    "MonitoringSessionDetailResponse",
    "SnapshotResponse",
    "VideoUploadResponse",
    "VideoProcessRequest",
    "VideoProcessResponse",
    "InventoryItemCreate",
    "InventoryItemUpdate",
    "InventoryItemResponse",
    "InventoryRowError",
    "InventoryParsedItem",
    "InventoryUploadPreviewResponse",
    "InventoryConfirmRequest",
    "InventoryConfirmResponse",
    "AlertResponse",
    "AlertStatusUpdate",
    "AlertEvidenceResponse",
    "AlertReviewRequest",
    "AlertGenerationResponse",
    "AlertSummaryResponse",
    "DetectionBoxSchema",
    "ProcessSnapshotAttendanceRequest",
    "ProcessSessionAttendanceRequest",
    "AttendanceObservationResponse",
    "ProcessSessionAttendanceResponse",
    "DetectedAssetSummary",
    "ProcessSnapshotInfrastructureRequest",
    "ProcessSessionInfrastructureRequest",
    "InfrastructureObservationResponse",
    "SnapshotInfrastructureResponse",
    "ProcessSessionInfrastructureResponse",
    "AttendanceComplianceSchema",
    "InfrastructureComplianceItemSchema",
    "CalculateComplianceRequest",
    "SessionComplianceResponse",
    "ComplianceDashboardSummaryResponse",
    "DashboardCentresSummary",
    "DashboardSessionsSummary",
    "DashboardAlertsSummary",
    "DashboardComplianceSummary",
    "DashboardSummaryResponse",
    "CentreOverviewItem",
    "RecentActivityItem",
]

from backend.app.schemas.dashboard import (
    DashboardCentresSummary,
    DashboardSessionsSummary,
    DashboardAlertsSummary,
    DashboardComplianceSummary,
    DashboardSummaryResponse,
    CentreOverviewItem,
    RecentActivityItem,
)
