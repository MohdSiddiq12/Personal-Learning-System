"""Application settings loaded from environment variables and an optional .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values that are safe to omit in local development."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"
    data_dir: Path = Path("./data")
    llm_provider: str | None = None
    max_upload_mb: int = Field(default=50, gt=0)
    max_pages: int = Field(default=1500, gt=0)
    min_chars_per_page: int = Field(default=50, ge=0)
    ocr_suspect_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
