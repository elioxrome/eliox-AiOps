from typing import Protocol

from src.application.models import BuildAnalysis, ChatMessage


class BuildAnalyzer(Protocol):
    def analyze(self, prompt: str) -> BuildAnalysis: ...


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class ChatClient(Protocol):
    def chat(self, messages: list[ChatMessage]) -> str: ...
