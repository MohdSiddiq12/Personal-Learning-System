from pathlib import Path

from learnbook.config import Settings


def test_settings_load_defaults(monkeypatch) -> None:
    for name in ("LOG_LEVEL", "DATA_DIR", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"
    assert settings.data_dir == Path("./data")
    assert settings.llm_provider is None


def test_missing_optional_settings_do_not_crash(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_provider is None
