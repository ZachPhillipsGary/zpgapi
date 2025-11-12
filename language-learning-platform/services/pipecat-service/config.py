"""Configuration for Pipecat service."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Service
    SERVICE_NAME: str = "pipecat-language-tutoring"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    DATABASE_URL: str

    # Google Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # Gemini 2.0 Flash for multimodal

    # Daily.co (for WebRTC)
    DAILY_API_KEY: Optional[str] = None
    DAILY_ROOM_URL: Optional[str] = None

    # Audio settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024

    # Language settings
    SUPPORTED_LANGUAGES: dict = {
        "en": {"name": "English", "voice": "en-US-Neural2-F"},
        "fr": {"name": "French", "voice": "fr-FR-Neural2-A"},
        "zh-TW": {"name": "Mandarin (Traditional)", "voice": "cmn-TW-Wavenet-A"}
    }

    # Session settings
    MAX_SESSION_DURATION: int = 3600  # 1 hour in seconds
    IDLE_TIMEOUT: int = 300  # 5 minutes

    # Redis (for session management)
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
