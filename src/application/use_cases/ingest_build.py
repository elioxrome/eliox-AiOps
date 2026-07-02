from src.application.errors import ExternalServiceError
from src.application.failure_rules import detect_known_failure
from src.application.log_normalization import normalize_log_signature
from src.application.models import (
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.application.services.analysis_dispatcher import AnalysisDispatcher
from src.infrastructure.llm.base import BuildAnalyzer, Embedder
from src.infrastructure.llm.prompts import ANALYZE_BUILD_PROMPT
from src.infrastructure.persistence.base import (
    BuildRepositoryPort,
    KnownErrorRepositoryPort,
)


class IngestBuildUseCase:
    def __init__(
        self,
        repository: BuildRepositoryPort,
        known_errors: KnownErrorRepositoryPort,
        llm: BuildAnalyzer,
        embedder: Embedder,
        dispatcher: AnalysisDispatcher,
        max_log_characters: int,
        rag_enabled: bool = True,
        rag_similarity_threshold: float = 0.15,
    ) -> None:
        self.repository = repository
        self.known_errors = known_errors
        self.llm = llm
        self.embedder = embedder
        self.dispatcher = dispatcher
        self.max_log_characters = max_log_characters
        self.rag_enabled = rag_enabled
        self.rag_similarity_threshold = rag_similarity_threshold

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
        self.dispatcher.dispatch(build_id, build.status)
        return build_id, ProcessingStatus.QUEUED

    def process(self, build_id: int, status: BuildStatus) -> None:
        self.repository.mark_processing(build_id)
        try:
            log = self.repository.get_log(build_id)
            known_failure = detect_known_failure(log)
            if known_failure:
                self.repository.complete_analysis(build_id, known_failure)
                return

            signature = normalize_log_signature(log)
            embedding = self._embed_or_none(signature)

            if embedding is not None:
                match = self.known_errors.find_similar(
                    embedding, self.rag_similarity_threshold
                )
                if match:
                    self.repository.complete_analysis(
                        build_id, match.analysis, matched_known_error_id=match.id
                    )
                    self.known_errors.record_hit(match.id)
                    return

            prompt = ANALYZE_BUILD_PROMPT.format(
                status=status.value,
                log=log,
            )
            analysis = self.llm.analyze(prompt)
            self.repository.complete_analysis(build_id, analysis)

            if embedding is not None:
                self.known_errors.insert(signature, embedding, analysis, build_id)
        except (ExternalServiceError, KeyError) as exc:
            self.repository.fail(build_id, str(exc))

    def _embed_or_none(self, signature: str) -> list[float] | None:
        if not self.rag_enabled:
            return None
        try:
            return self.embedder.embed(signature)
        except ExternalServiceError:
            # RAG is a best-effort optimization: if the embedding provider
            # is unavailable, fall back to a plain LLM analysis instead of
            # failing the whole build.
            return None
