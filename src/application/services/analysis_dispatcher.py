from typing import Protocol

from src.application.models import BuildStatus


class AnalysisDispatcher(Protocol):
    def dispatch(self, build_id: int, status: BuildStatus) -> None: ...
