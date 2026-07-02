import json

import pytest
import requests

from src.application.errors import ExternalServiceError, InvalidLLMResponseError
from src.application.models import ChatMessage
from src.infrastructure.llm.ollama_client import OllamaClient


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


def test_returns_validated_analysis() -> None:
    analysis = {
        "category": "test",
        "root_cause": "Assertion failed",
        "confidence": 0.8,
        "recommendation": "Fix the expectation",
    }
    session = FakeSession({"response": json.dumps(analysis)})
    client = OllamaClient(
        "http://ollama:11434/",
        model="test-model",
        timeout_seconds=5,
        session=session,
    )

    result = client.analyze("prompt")

    assert result.root_cause == "Assertion failed"
    assert session.request == {
        "url": "http://ollama:11434/api/generate",
        "json": {
            "model": "test-model",
            "prompt": "prompt",
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 4_096,
                "num_predict": 400,
            },
        },
        "timeout": 5,
    }


def test_rejects_invalid_analysis_schema() -> None:
    session = FakeSession({"response": '{"confidence": 2}'})
    client = OllamaClient("http://ollama:11434", session=session)

    with pytest.raises(InvalidLLMResponseError):
        client.analyze("prompt")


def test_includes_ollama_error_detail() -> None:
    session = FakeSession(
        {"error": "model 'missing' not found"},
        status_code=404,
    )
    client = OllamaClient("http://ollama:11434", session=session)

    with pytest.raises(
        ExternalServiceError,
        match="model 'missing' not found",
    ):
        client.analyze("prompt")


def test_chat_returns_assistant_reply() -> None:
    session = FakeSession({"message": {"role": "assistant", "content": "Hola"}})
    client = OllamaClient("http://ollama:11434", model="test-model", session=session)

    reply = client.chat([ChatMessage(role="user", content="Hola")])

    assert reply == "Hola"
    assert session.request["url"] == "http://ollama:11434/api/chat"
    assert session.request["json"]["messages"] == [
        {"role": "user", "content": "Hola"}
    ]


def test_chat_rejects_missing_message() -> None:
    session = FakeSession({})
    client = OllamaClient("http://ollama:11434", session=session)

    with pytest.raises(InvalidLLMResponseError):
        client.chat([ChatMessage(role="user", content="Hola")])
