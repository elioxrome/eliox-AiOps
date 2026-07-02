from src.application.models import BuildAnalysis, BuildIngest, BuildStatus
from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)


class FakeJenkins:
    build_number = 7

    def list_latest_completed_builds(
        self,
        included_jobs: tuple[str, ...],
    ) -> list[BuildIngest]:
        assert included_jobs == ("*",)
        return [
            BuildIngest(
                job_name="broken-pipeline",
                build_number=self.build_number,
                status=BuildStatus.FAILURE,
                log="WorkflowScript: 14: Expected a step",
            )
        ]


class FakeLLM:
    calls = 0

    def analyze(self, prompt: str) -> BuildAnalysis:
        self.calls += 1
        return BuildAnalysis(
            category="pipeline_syntax",
            root_cause="Declarative Pipeline expected a valid step on line 14.",
            confidence=0.99,
            recommendation="Remove or wrap the invalid Groovy expression.",
        )


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        raise AssertionError(
            "the regex rule should short-circuit before an embedding is needed"
        )


class InlineDispatcher:
    """Runs analysis synchronously, standing in for the Celery queue in
    tests so assertions can run right after `scan_once()` returns."""

    def __init__(self) -> None:
        self.ingestion: IngestBuildUseCase | None = None

    def dispatch(self, build_id: int, status: BuildStatus) -> None:
        assert self.ingestion is not None
        self.ingestion.process(build_id, status)


def test_monitor_imports_pipeline_compilation_failure_once(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    llm = FakeLLM()
    dispatcher = InlineDispatcher()
    ingestion = IngestBuildUseCase(
        repository,
        known_error_repository,
        llm,
        FakeEmbedder(),
        dispatcher,
        10_000,
    )
    dispatcher.ingestion = ingestion
    jenkins = FakeJenkins()
    monitor = JenkinsMonitor(
        jenkins,
        repository,
        ingestion,
        dispatcher,
        jobs=("*",),
        interval_seconds=15,
    )

    assert monitor.scan_once() == 0
    jenkins.build_number = 8
    assert monitor.scan_once() == 1
    assert monitor.scan_once() == 0

    builds = repository.list_recent()
    assert len(builds) == 1
    assert builds[0].category == "sintaxis_pipeline"
    assert llm.calls == 0
