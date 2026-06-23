from pathlib import Path

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.infrastructure.persistence.build_repository import BuildRepository


class FakeLLM:
    calls = 0

    def analyze(self, prompt: str) -> BuildAnalysis:
        self.calls += 1
        assert "UNSTABLE" in prompt
        return BuildAnalysis(
            category="tests",
            root_cause="Flaky test",
            confidence=0.88,
            recommendation="Quarantine and fix the test",
        )


def make_repository(tmp_path: Path) -> BuildRepository:
    repository = BuildRepository(str(tmp_path / "builds.db"))
    repository.initialize()
    return repository


def test_success_is_completed_without_calling_llm(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    llm = FakeLLM()
    use_case = IngestBuildUseCase(repository, llm, 1_000)

    build_id, processing = use_case.receive(
        BuildIngest(
            job_name="deploy",
            build_number=1,
            status=BuildStatus.SUCCESS,
            log="Everything passed",
        )
    )

    record = repository.get(build_id)
    assert processing == ProcessingStatus.COMPLETED
    assert record is not None
    assert record.category == "éxito"
    assert llm.calls == 0


def test_unstable_build_is_analyzed(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    llm = FakeLLM()
    use_case = IngestBuildUseCase(repository, llm, 1_000)
    build = BuildIngest(
        job_name="tests",
        build_number=2,
        status=BuildStatus.UNSTABLE,
        log="test_checkout failed intermittently",
    )

    build_id, processing = use_case.receive(build)
    use_case.process(build_id, build.status)

    record = repository.get(build_id)
    assert processing == ProcessingStatus.QUEUED
    assert record is not None
    assert record.processing_status == ProcessingStatus.COMPLETED
    assert record.root_cause == "Flaky test"
    assert llm.calls == 1


def test_feedback_is_persisted(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    build_id = repository.save_received(
        BuildIngest(
            job_name="deploy",
            build_number=3,
            status=BuildStatus.SUCCESS,
        ),
        ProcessingStatus.COMPLETED,
        1_000,
    )

    assert repository.rate(build_id, 1, "Correct diagnosis")
    record = repository.get(build_id)
    assert record is not None
    assert record.rating == 1
    assert record.feedback_comment == "Correct diagnosis"


def test_clear_keeps_monitor_cursor(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    repository.mark_build_observed("deploy", 10)
    repository.save_received(
        BuildIngest(
            job_name="deploy",
            build_number=10,
            status=BuildStatus.SUCCESS,
        ),
        ProcessingStatus.COMPLETED,
        1_000,
    )

    assert repository.clear_builds() == 1
    assert repository.list_recent() == []
    assert repository.get_last_observed_build("deploy") == 10
