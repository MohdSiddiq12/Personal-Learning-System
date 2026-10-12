from pathlib import Path

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
