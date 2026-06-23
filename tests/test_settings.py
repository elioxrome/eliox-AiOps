import pytest

from src.config import Settings


def test_loads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JENKINS_URL", "http://jenkins.example/")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
    monkeypatch.setenv("MAX_LOG_CHARACTERS", "25000")

    settings = Settings.from_env()

    assert settings.jenkins_url == "http://jenkins.example"
    assert settings.ollama_model == "custom-model"
    assert settings.max_log_characters == 25_000


def test_rejects_non_positive_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_LOG_CHARACTERS", "0")

    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()
