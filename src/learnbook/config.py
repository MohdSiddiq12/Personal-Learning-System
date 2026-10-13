"""Application settings loaded from environment variables and an optional .env file."""

from pathlib import Path

from pydantic import Field, SecretStr, model_validator
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
    environment: str = "development"
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
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None
    groq_timeout_seconds: int = Field(default=60, gt=0)
    groq_max_retries: int = Field(default=3, ge=0, le=10)
    groq_max_request_tokens: int = Field(default=5000, gt=0)
    groq_tpm_limit: int = Field(default=6000, gt=0)
    groq_daily_token_budget: int = Field(default=150_000, gt=0)
    groq_max_total_wait_seconds: int = Field(default=90, ge=0)
    groq_json_mode_supported: bool = False
    max_books_per_user_per_day: int = Field(default=2, gt=0)
    max_lessons_per_user_per_day: int = Field(default=12, gt=0)
    ai_daily_summary_limit: int = Field(default=3, gt=0)
    ai_monthly_summary_limit: int = Field(default=500, gt=0)
    ai_max_book_chars: int = Field(default=400_000, gt=0)

    @model_validator(mode="after")
    def production_requires_groq_settings(self) -> "Settings":
        if self.environment.lower() == "production":
            if not self.groq_model or not self.groq_model.strip():
                raise ValueError("GROQ_MODEL must be set in production.")
            if (
                not self.groq_api_key
                or not self.groq_api_key.get_secret_value().strip()
            ):
                raise ValueError("GROQ_API_KEY must be set in production.")
        return self
