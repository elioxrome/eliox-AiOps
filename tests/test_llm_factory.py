from src.config import Settings
from src.infrastructure.llm.factory import create_build_analyzer
from src.infrastructure.llm.ollama_client import OllamaClient
from src.infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)


def test_creates_ollama_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    analyzer = create_build_analyzer(Settings.from_env())
    assert isinstance(analyzer, OllamaClient)


def test_creates_openai_compatible_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example/v1")
    monkeypatch.setenv("LLM_MODEL", "model")
    analyzer = create_build_analyzer(Settings.from_env())
    assert isinstance(analyzer, OpenAICompatibleClient)
