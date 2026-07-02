import json

import pytest
import requests

from src.application.errors import ExternalServiceError
from src.application.models import ChatMessage
from src.infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
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


def test_returns_validated_openai_compatible_analysis() -> None:
    analysis = {
        "category": "autenticación",
        "root_cause": "El token expiró",
        "confidence": 0.95,
        "recommendation": "Renueva la credencial",
    }
    session = FakeSession(
        {
            "choices": [
                {"message": {"content": json.dumps(analysis)}}
            ]
        }
    )
    client = OpenAICompatibleClient(
        "http://llm.example/v1/",
        "test-model",
        api_key="secret",
        timeout_seconds=10,
        temperature=0.2,
        max_output_tokens=500,
        json_mode=True,
        session=session,
    )

    result = client.analyze("prompt")

    assert result.category == "autenticación"
    assert session.request == {
        "url": "http://llm.example/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
        },
        "json": {
            "model": "test-model",
            "messages": [{"role": "user", "content": "prompt"}],
            "temperature": 0.2,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        },
        "timeout": 10,
    }


def test_exposes_provider_error_message() -> None:
    session = FakeSession(
        {"error": {"message": "Invalid API key"}},
        status_code=401,
    )
    client = OpenAICompatibleClient(
        "https://api.example/v1",
        "model",
        session=session,
    )

    with pytest.raises(ExternalServiceError, match="Invalid API key"):
        client.analyze("prompt")


def test_chat_returns_assistant_reply() -> None:
    session = FakeSession(
        {"choices": [{"message": {"content": "Revisa el disco"}}]}
    )
    client = OpenAICompatibleClient(
        "https://api.example/v1", "test-model", session=session
    )

    reply = client.chat([ChatMessage(role="user", content="¿Por qué falló?")])

    assert reply == "Revisa el disco"
    assert session.request["url"] == "https://api.example/v1/chat/completions"
    assert session.request["json"]["messages"] == [
        {"role": "user", "content": "¿Por qué falló?"}
    ]
