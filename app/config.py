"""Application configuration managed via Pydantic Settings.

Reads settings from environment variables and .env file.
"""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for CivicFlow."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = Field(default_factory=lambda: Path("uploads"))
    AUDIO_OUTPUT_DIR: Path = Field(default_factory=lambda: Path("audio_cache"))

    # App Environment
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Provider Configuration
    GEMINI_API_KEY: str = ""
    MODEL_FAST: str = "gemini-2.5-flash"
    MODEL_STRONG: str = "gemini-2.5-pro"
    LLM_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3

    # Language and Localization
    SUPPORTED_LANGUAGES: List[str] = ["hi", "en", "mr", "ta", "te", "bn"]
    DEFAULT_LANGUAGE: str = "hi"

    # Storage and Persistence
    SQLITE_DB_PATH: str = "civicflow_checkpoints.sqlite"

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()

