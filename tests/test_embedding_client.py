import pytest
import requests

from src.application.errors import ExternalServiceError, InvalidLLMResponseError
from src.infrastructure.llm.embedding_client import (
    OllamaEmbeddingClient,
    OpenAICompatibleEmbeddingClient,
)


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.request: dict | None = None

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.request = {"url": url, **kwargs}
        return FakeResponse(self.payload, self.status_code)


def test_ollama_embedder_returns_vector() -> None:
    session = FakeSession({"embedding": [0.1, 0.2, 0.3]})
    client = OllamaEmbeddingClient(
        "http://ollama:11434/", "embeddinggemma", session=session
    )

    vector = client.embed("connection timeout")

    assert vector == [0.1, 0.2, 0.3]
    assert session.request["url"] == "http://ollama:11434/api/embeddings"
    assert session.request["json"] == {
        "model": "embeddinggemma",
        "prompt": "connection timeout",
    }


def test_ollama_embedder_rejects_missing_vector() -> None:
    session = FakeSession({})
    client = OllamaEmbeddingClient(
        "http://ollama:11434", "embeddinggemma", session=session
    )

    with pytest.raises(InvalidLLMResponseError):
        client.embed("text")


def test_ollama_embedder_translates_http_errors() -> None:
    session = FakeSession({"error": "model not found"}, status_code=404)
    client = OllamaEmbeddingClient(
        "http://ollama:11434", "embeddinggemma", session=session
    )

    with pytest.raises(ExternalServiceError, match="model not found"):
        client.embed("text")


def test_openai_compatible_embedder_returns_vector() -> None:
    session = FakeSession({"data": [{"embedding": [0.4, 0.5]}]})
    client = OpenAICompatibleEmbeddingClient(
        "https://api.example/v1",
        "text-embedding-3-small",
        api_key="secret",
        session=session,
    )

    vector = client.embed("connection timeout")

    assert vector == [0.4, 0.5]
    assert session.request["url"] == "https://api.example/v1/embeddings"
    assert session.request["headers"]["Authorization"] == "Bearer secret"
    assert session.request["json"] == {
        "model": "text-embedding-3-small",
        "input": "connection timeout",
    }


def test_openai_compatible_embedder_translates_provider_error() -> None:
    session = FakeSession({"error": {"message": "Invalid API key"}}, status_code=401)
    client = OpenAICompatibleEmbeddingClient(
        "https://api.example/v1", "model", session=session
    )

    with pytest.raises(ExternalServiceError, match="Invalid API key"):
        client.embed("text")
