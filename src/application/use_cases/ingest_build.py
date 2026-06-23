from src.application.errors import ExternalServiceError
from src.application.failure_rules import detect_known_failure
from src.application.models import (
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.application.use_cases.analyze_build import BuildAnalyzer
from src.infrastructure.llm.prompts import ANALYZE_BUILD_PROMPT
from src.infrastructure.persistence.build_repository import BuildRepository


class IngestBuildUseCase:
    def __init__(
        self,
        repository: BuildRepository,
        llm: BuildAnalyzer,
        max_log_characters: int,
    ) -> None:
        self.repository = repository
        self.llm = llm
        self.max_log_characters = max_log_characters

    def receive(self, build: BuildIngest) -> tuple[int, ProcessingStatus]:
        requires_analysis = build.status in {
            BuildStatus.FAILURE,
            BuildStatus.UNSTABLE,
        }
        if not requires_analysis:
            build_id = self.repository.save_received(
                build,
                ProcessingStatus.COMPLETED,
                self.max_log_characters,
            )
            if build.status == BuildStatus.SUCCESS:
                self.repository.complete_success(build_id)
            else:
                self.repository.complete_without_analysis(
                    build_id,
                    category=build.status.value.lower(),
                    root_cause=(
                        "La ejecución terminó con el estado "
                        f"{build.status.value}."
                    ),
                    recommendation=(
                        "Revisa la ejecución en Jenkins si este estado "
                        "no era esperado."
                    ),
                )
            return build_id, ProcessingStatus.COMPLETED

        build_id = self.repository.save_received(
            build,
            ProcessingStatus.QUEUED,
            self.max_log_characters,
        )
        return build_id, ProcessingStatus.QUEUED

    def process(self, build_id: int, status: BuildStatus) -> None:
        self.repository.mark_processing(build_id)
        try:
            log = self.repository.get_log(build_id)
            known_failure = detect_known_failure(log)
            if known_failure:
                self.repository.complete_analysis(build_id, known_failure)
                return
            prompt = ANALYZE_BUILD_PROMPT.format(
                status=status.value,
                log=log,
            )
            analysis = self.llm.analyze(prompt)
            self.repository.complete_analysis(build_id, analysis)
        except (ExternalServiceError, KeyError) as exc:
            self.repository.fail(build_id, str(exc))
