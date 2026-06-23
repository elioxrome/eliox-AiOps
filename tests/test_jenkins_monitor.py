from pathlib import Path

from src.application.models import BuildAnalysis, BuildIngest, BuildStatus
from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.infrastructure.persistence.build_repository import BuildRepository


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


def test_monitor_imports_pipeline_compilation_failure_once(
    tmp_path: Path,
) -> None:
    repository = BuildRepository(str(tmp_path / "builds.db"))
    repository.initialize()
    llm = FakeLLM()
    ingestion = IngestBuildUseCase(repository, llm, 10_000)
    monitor = JenkinsMonitor(
        FakeJenkins(),
        repository,
        ingestion,
        jobs=("*",),
        interval_seconds=15,
    )

    assert monitor.scan_once() == 0
    monitor.jenkins.build_number = 8
    assert monitor.scan_once() == 1
    assert monitor.scan_once() == 0

    builds = repository.list_recent()
    assert len(builds) == 1
    assert builds[0].category == "sintaxis_pipeline"
    assert llm.calls == 0
