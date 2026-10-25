"""Application configuration using Pydantic Settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core Application Settings
    APP_NAME: str = "Stithi-AI-Monitoring"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database Configuration (MySQL expected name: sih_monitoring)
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/sih_monitoring"

    # JWT Authentication Settings
    # In production, set JWT_SECRET_KEY via environment variable or secret manager
    JWT_SECRET_KEY: str = "sih-ai-monitoring-dev-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Storage Directories
    STORAGE_ROOT: str = "storage"
    SNAPSHOT_DIR: str = "snapshots"
    VIDEO_DIR: str = "videos"
    EVIDENCE_DIR: str = "evidence"
    DATASET_DIR: str = "datasets"
    AI_MODELS_DIR: str = "ai_models"

    # Compliance & Video Snapshot Settings
    DEFAULT_ATTENDANCE_TOLERANCE: int = 2
    COMPLIANCE_ATTENDANCE_TOLERANCE: int = 2
    COMPLIANCE_AGGREGATION_METHOD: str = "MEDIAN"  # MEDIAN, MEAN
    COMPLIANCE_INFRASTRUCTURE_RULE: str = "observed_gte_expected"
    ALERT_ATTENDANCE_LOW_THRESHOLD: int = 3      # difference <= 3 -> LOW
    ALERT_ATTENDANCE_MEDIUM_THRESHOLD: int = 7   # difference <= 7 -> MEDIUM, > 7 -> HIGH
    ALERT_INFRASTRUCTURE_LOW_THRESHOLD: int = 1  # difference <= 1 -> LOW
    ALERT_INFRASTRUCTURE_MEDIUM_THRESHOLD: int = 4 # difference <= 4 -> MEDIUM, > 4 -> HIGH
    SNAPSHOT_INTERVAL_SECONDS: int = 10
    MAX_SNAPSHOTS_PER_SESSION: int = 300
    MAX_VIDEO_DURATION_SECONDS: int = 7200  # 2 hours
    MAX_VIDEO_FILE_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB
    SNAPSHOT_IMAGE_FORMAT: str = "jpg"
    JPEG_QUALITY: int = 85

    # AI Model Strategy (Stithi AI - YOLO26x high-precision architecture)
    ATTENDANCE_MODEL_FAMILY: str = "Stithi AI"
    ATTENDANCE_MODEL_TYPE: str = "yolo26x"
    ATTENDANCE_MODEL_NAME: str = "Stithi AI - Presence Detector"
    ATTENDANCE_MODEL_VERSION: str = "v26x-precision"
    ATTENDANCE_MODEL_PATH: str = "ai_models/yolo26_face_presence.pt"
    ATTENDANCE_CONFIDENCE_THRESHOLD: float = 0.40
    ATTENDANCE_IOU_THRESHOLD: float = 0.45
    ATTENDANCE_DEVICE: str = "cpu"  # "cpu", "cuda", "mps"
    ATTENDANCE_SAVE_ANNOTATED: bool = True
    INFRASTRUCTURE_MODEL_FAMILY: str = "Stithi AI"
    INFRASTRUCTURE_MODEL_TYPE: str = "yolo26x"
    INFRASTRUCTURE_MODEL_NAME: str = "Stithi AI - Asset Detector"
    INFRASTRUCTURE_MODEL_VERSION: str = "v26x-precision"
    INFRASTRUCTURE_MODEL_PATH: str = "ai_models/yolo26_infrastructure.pt"
    INFRASTRUCTURE_CONFIDENCE_THRESHOLD: float = 0.25
    INFRASTRUCTURE_IOU_THRESHOLD: float = 0.50
    INFRASTRUCTURE_DEVICE: str = "cpu"  # "cpu", "cuda", "mps"
    INFRASTRUCTURE_SAVE_ANNOTATED: bool = True
    AI_INFERENCE_IMGSZ: int = 1280  # Precision-focused high-resolution input dimension

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
