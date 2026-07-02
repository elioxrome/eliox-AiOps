import hashlib

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)


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


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        digest = hashlib.sha256(text.encode()).digest()[:8]
        return [byte / 255 for byte in digest]


class FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[tuple[int, BuildStatus]] = []

    def dispatch(self, build_id: int, status: BuildStatus) -> None:
        self.dispatched.append((build_id, status))


def make_use_case(
    repository: BuildRepository,
    known_errors: KnownErrorRepository,
    llm: FakeLLM,
    embedder: FakeEmbedder | None = None,
    dispatcher: FakeDispatcher | None = None,
) -> IngestBuildUseCase:
    return IngestBuildUseCase(
        repository,
        known_errors,
        llm,
        embedder or FakeEmbedder(),
        dispatcher or FakeDispatcher(),
        1_000,
    )


def test_success_is_completed_without_calling_llm(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    llm = FakeLLM()
    use_case = make_use_case(repository, known_error_repository, llm)

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


def test_unstable_build_is_analyzed(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    llm = FakeLLM()
    dispatcher = FakeDispatcher()
    use_case = make_use_case(
        repository, known_error_repository, llm, dispatcher=dispatcher
    )
    build = BuildIngest(
        job_name="tests",
        build_number=2,
        status=BuildStatus.UNSTABLE,
        log="test_checkout failed intermittently",
    )

    build_id, processing = use_case.receive(build)
    assert dispatcher.dispatched == [(build_id, BuildStatus.UNSTABLE)]
    use_case.process(build_id, build.status)

    record = repository.get(build_id)
    assert processing == ProcessingStatus.QUEUED
    assert record is not None
    assert record.processing_status == ProcessingStatus.COMPLETED
    assert record.root_cause == "Flaky test"
    assert record.matched_known_error_id is None
    assert llm.calls == 1


def test_similar_failure_reuses_known_error(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    llm = FakeLLM()
    use_case = make_use_case(repository, known_error_repository, llm)
    log = "test_checkout failed intermittently"

    first = BuildIngest(
        job_name="tests", build_number=10, status=BuildStatus.UNSTABLE, log=log
    )
    first_id, _ = use_case.receive(first)
    use_case.process(first_id, first.status)
    assert llm.calls == 1

    second = BuildIngest(
        job_name="tests", build_number=11, status=BuildStatus.UNSTABLE, log=log
    )
    second_id, _ = use_case.receive(second)
    use_case.process(second_id, second.status)

    record = repository.get(second_id)
    assert record is not None
    assert record.processing_status == ProcessingStatus.COMPLETED
    assert record.root_cause == "Flaky test"
    assert record.matched_known_error_id is not None
    assert llm.calls == 1


def test_feedback_is_persisted(repository: BuildRepository) -> None:
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


def test_clear_keeps_monitor_cursor(repository: BuildRepository) -> None:
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
