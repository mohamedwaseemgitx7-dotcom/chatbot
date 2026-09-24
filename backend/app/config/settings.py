"""
Application Settings & Environment Configurations
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved independently of the current working directory
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"  # development | production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Comma-separated browser origins allowed to call the API. CORS_ORIGINS is accepted as an alias.
    ALLOWED_ORIGINS: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173", validation_alias=AliasChoices("CORS_ORIGINS", "ALLOWED_ORIGINS")
    )
    # Read the client IP from X-Forwarded-For (only behind a trusted proxy such as Render).
    TRUST_PROXY_HEADERS: bool = False

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    STORAGE_BUCKET_NAME: str = "farmer-images"

    RATE_LIMIT_CHAT: str = "20/minute"
    RATE_LIMIT_IMAGE: str = "5/minute"
    RATE_LIMIT_VOICE: str = "5/minute"

    # Retrieval: minimum (cosine + crop/topic adjustments) score for a knowledge record to be used.
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.61  # calibrated: ai/evaluation/evaluate_retrieval.py
    # Vision: minimum top-class probability before a prediction is shown.
    IMAGE_CONFIDENCE_THRESHOLD: float = 0.60
    MAX_IMAGE_BYTES: int = 5 * 1024 * 1024

    # Voice (faster-whisper). Off by default: it needs ~1 GB RAM, more than Render's free instance.
    VOICE_ENABLED: bool = False
    VOICE_MODEL_SIZE: str = "small"
    MAX_AUDIO_BYTES: int = 10 * 1024 * 1024
    MAX_AUDIO_SECONDS: int = 60

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [origin.strip().rstrip("/") for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        # A wildcard is never allowed in production.
        return [o for o in origins if o != "*"] if self.is_production else origins

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", populate_by_name=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
