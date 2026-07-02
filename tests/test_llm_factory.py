import pytest

from src.config import Settings
from src.infrastructure.llm.embedding_client import (
    OllamaEmbeddingClient,
    OpenAICompatibleEmbeddingClient,
)
from src.infrastructure.llm.factory import (
    create_build_analyzer,
    create_chat_model,
    create_embedder,
)
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


def test_chat_model_reuses_the_generation_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    chat_model = create_chat_model(Settings.from_env())
    assert isinstance(chat_model, OllamaClient)


def test_creates_ollama_embedder(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    embedder = create_embedder(Settings.from_env())
    assert isinstance(embedder, OllamaEmbeddingClient)


def test_creates_openai_compatible_embedder(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai-compatible")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://api.example/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedder = create_embedder(Settings.from_env())
    assert isinstance(embedder, OpenAICompatibleEmbeddingClient)


def test_rejects_unsupported_embedding_provider(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported EMBEDDING_PROVIDER"):
        create_embedder(Settings.from_env())
