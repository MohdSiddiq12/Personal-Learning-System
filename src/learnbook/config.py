"""Application settings loaded from environment variables and an optional .env file."""

from pathlib import Path

from pydantic import Field, SecretStr
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
    pdf_processing_timeout_seconds: int = Field(default=30, gt=0)
    max_concurrent_ingestions: int = Field(default=2, gt=0)
    public_max_pages: int = Field(default=500, gt=0)
    max_extracted_chars: int = Field(default=3_000_000, gt=0)
    max_books_per_user: int = Field(default=20, gt=0)
    max_user_storage_mb: int = Field(default=100, gt=0)
    upload_daily_limit: int = Field(default=10, gt=0)
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    gemini_model: str = "gemini-3.8-flash"
    ai_daily_summary_limit: int = Field(default=3, gt=0)
    ai_monthly_summary_limit: int = Field(default=500, gt=0)
    ai_max_book_chars: int = Field(default=400_000, gt=0)
