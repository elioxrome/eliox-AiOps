import asyncio
import logging
from typing import Protocol

from src.application.errors import ExternalServiceError
from src.application.models import BuildIngest
from src.application.services.analysis_dispatcher import AnalysisDispatcher
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.infrastructure.persistence.base import BuildRepositoryPort

logger = logging.getLogger(__name__)


class JenkinsBuildSource(Protocol):
    def list_latest_completed_builds(
        self,
        included_jobs: tuple[str, ...],
    ) -> list[BuildIngest]: ...


class JenkinsMonitor:
    def __init__(
        self,
        jenkins: JenkinsBuildSource,
        repository: BuildRepositoryPort,
        ingestion: IngestBuildUseCase,
        dispatcher: AnalysisDispatcher,
        jobs: tuple[str, ...],
        interval_seconds: int,
    ) -> None:
        self.jenkins = jenkins
        self.repository = repository
        self.ingestion = ingestion
        self.dispatcher = dispatcher
        self.jobs = jobs
        self.interval_seconds = interval_seconds

    def scan_once(self) -> int:
        imported = 0
        for build in self.jenkins.list_latest_completed_builds(self.jobs):
            last_observed = self.repository.get_last_observed_build(build.job_name)
            if last_observed is None:
                self.repository.mark_build_observed(
                    build.job_name,
                    build.build_number,
                )
                continue
            if build.build_number <= last_observed:
                continue
            self.repository.mark_build_observed(
                build.job_name,
                build.build_number,
            )
            if self.repository.exists(build.job_name, build.build_number):
                continue
            self.ingestion.receive(build)
            imported += 1

        for build_id, build_status in self.repository.list_pending():
            self.dispatcher.dispatch(build_id, build_status)
        return imported

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                imported = await asyncio.to_thread(self.scan_once)
                if imported:
                    logger.info("Imported %s Jenkins build(s)", imported)
            except ExternalServiceError:
                logger.exception("Jenkins monitor scan failed")

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=self.interval_seconds,
                )
            except TimeoutError:
                continue
