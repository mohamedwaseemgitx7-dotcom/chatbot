"""
FastAPI Route Dependencies & Security Injection
"""
from app.config.settings import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()
