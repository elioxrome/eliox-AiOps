import pytest

from src.config import Settings


def test_loads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JENKINS_URL", "http://jenkins.example/")
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.example/v1/")
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("MAX_LOG_CHARACTERS", "25000")

    settings = Settings.from_env()

    assert settings.jenkins_url == "http://jenkins.example"
    assert settings.llm_provider == "openai-compatible"
    assert settings.llm_base_url == "http://llm.example/v1"
    assert settings.llm_model == "custom-model"
    assert settings.max_log_characters == 25_000


def test_rejects_non_positive_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_LOG_CHARACTERS", "0")

    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()


def test_supports_legacy_ollama_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://legacy-ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "legacy-model")

    settings = Settings.from_env()

    assert settings.llm_provider == "ollama"
    assert settings.llm_base_url == "http://legacy-ollama:11434"
    assert settings.llm_model == "legacy-model"
