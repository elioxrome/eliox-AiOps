from dataclasses import dataclass
from typing import Protocol

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildRecord,
    BuildStatus,
    ChatMessage,
    ProcessingStatus,
)


@dataclass(frozen=True)
class KnownErrorMatch:
    id: int
    analysis: BuildAnalysis
    distance: float


class BuildRepositoryPort(Protocol):
    def save_received(
        self,
        build: BuildIngest,
        processing_status: ProcessingStatus,
        max_log_characters: int,
    ) -> int: ...

    def mark_processing(self, build_id: int) -> None: ...

    def complete_success(self, build_id: int) -> None: ...

    def complete_without_analysis(
        self,
        build_id: int,
        category: str,
        root_cause: str,
        recommendation: str,
    ) -> None: ...

    def complete_analysis(
        self,
        build_id: int,
        analysis: BuildAnalysis,
        matched_known_error_id: int | None = None,
    ) -> None: ...

    def fail(self, build_id: int, error: str) -> None: ...

    def get_log(self, build_id: int) -> str: ...

    def get(self, build_id: int) -> BuildRecord | None: ...

    def list_pending(self) -> list[tuple[int, BuildStatus]]: ...

    def get_last_observed_build(self, job_name: str) -> int | None: ...

    def mark_build_observed(self, job_name: str, build_number: int) -> None: ...

    def exists(self, job_name: str, build_number: int) -> bool: ...

    def add_chat_message(self, build_id: int, role: str, content: str) -> None: ...

    def list_chat_messages(self, build_id: int) -> list[ChatMessage]: ...


class KnownErrorRepositoryPort(Protocol):
    def find_similar(
        self,
        embedding: list[float],
        threshold: float,
    ) -> KnownErrorMatch | None: ...

    def record_hit(self, known_error_id: int) -> None: ...

    def insert(
        self,
        signature: str,
        embedding: list[float],
        analysis: BuildAnalysis,
        source_build_id: int,
    ) -> int: ...

    def adjust_trust(self, known_error_id: int, rating: int) -> None: ...
