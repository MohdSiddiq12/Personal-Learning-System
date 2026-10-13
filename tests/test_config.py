from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from learnbook.config import Settings


def test_settings_load_defaults(monkeypatch) -> None:
    for name in (
        "LOG_LEVEL",
        "DATA_DIR",
        "LLM_PROVIDER",
        "MAX_UPLOAD_MB",
        "MAX_PAGES",
        "MIN_CHARS_PER_PAGE",
        "OCR_SUSPECT_RATIO",
        "ENVIRONMENT",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_TIMEOUT_SECONDS",
        "GROQ_MAX_RETRIES",
        "GROQ_MAX_REQUEST_TOKENS",
        "GROQ_TPM_LIMIT",
        "GROQ_DAILY_TOKEN_BUDGET",
        "GROQ_MAX_TOTAL_WAIT_SECONDS",
        "GROQ_JSON_MODE_SUPPORTED",
        "MAX_BOOKS_PER_USER_PER_DAY",
        "MAX_LESSONS_PER_USER_PER_DAY",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"
    assert settings.data_dir == Path("./data")
    assert settings.llm_provider is None
    assert settings.max_upload_mb == 50
    assert settings.max_pages == 1500
    assert settings.min_chars_per_page == 50
    assert settings.ocr_suspect_ratio == 0.8


def test_missing_optional_settings_do_not_crash(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_provider is None


def test_ingestion_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "12")
    monkeypatch.setenv("MAX_PAGES", "25")
    monkeypatch.setenv("MIN_CHARS_PER_PAGE", "8")
    monkeypatch.setenv("OCR_SUSPECT_RATIO", "0.6")

    settings = Settings(_env_file=None)

    assert settings.max_upload_mb == 12
    assert settings.max_pages == 25
    assert settings.min_chars_per_page == 8
    assert settings.ocr_suspect_ratio == 0.6


def test_groq_production_requires_server_model_and_key() -> None:
    with pytest.raises(ValidationError, match="GROQ_MODEL must be set in production"):
        Settings(_env_file=None, environment="production")
    with pytest.raises(ValidationError, match="GROQ_API_KEY must be set in production"):
        Settings(
            _env_file=None, environment="production", groq_model="configured-model"
        )
    settings = Settings(
        _env_file=None,
        environment="production",
        groq_model="configured-model",
        groq_api_key=SecretStr("a-server-side-secret-key"),
    )
    assert settings.groq_model == "configured-model"


def test_groq_limits_are_overridable_without_a_groq_sdk() -> None:
    settings = Settings(
        _env_file=None,
        groq_timeout_seconds=25,
        groq_max_retries=1,
        groq_max_request_tokens=4200,
        groq_tpm_limit=5100,
        groq_daily_token_budget=90000,
        max_books_per_user_per_day=1,
        max_lessons_per_user_per_day=7,
    )
    assert settings.groq_timeout_seconds == 25
    assert settings.groq_max_retries == 1
    assert settings.groq_max_request_tokens == 4200
    assert settings.groq_tpm_limit == 5100
    assert settings.groq_daily_token_budget == 90000
    assert settings.max_books_per_user_per_day == 1
    assert settings.max_lessons_per_user_per_day == 7
