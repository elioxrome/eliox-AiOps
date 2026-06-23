from typing import Protocol

from src.application.models import BuildAnalysis


class BuildAnalyzer(Protocol):
    def analyze(self, prompt: str) -> BuildAnalysis: ...
