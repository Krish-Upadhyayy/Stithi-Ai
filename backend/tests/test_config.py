"""Configuration loading tests."""

from backend.app.core.config import settings


def test_configuration_loading():
    assert settings.APP_NAME in ["SIH-Centre-AI-Monitoring", "Stithi-AI-Monitoring"]
    assert settings.API_PREFIX == "/api/v1"
    assert "sih_monitoring" in settings.DATABASE_URL
    assert settings.DEFAULT_ATTENDANCE_TOLERANCE >= 0
    assert settings.SNAPSHOT_INTERVAL_SECONDS > 0
