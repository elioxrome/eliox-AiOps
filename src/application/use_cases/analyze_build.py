from typing import Protocol

from src.application.models import BuildAnalysis
from src.infrastructure.llm.prompts import ANALYZE_BUILD_PROMPT


class BuildLogProvider(Protocol):
    def get_build_log(self, job_name: str, build_number: int) -> str: ...


class BuildAnalyzer(Protocol):
    def analyze(self, prompt: str) -> BuildAnalysis: ...


class AnalyzeBuildUseCase:
    def __init__(
        self,
        jenkins: BuildLogProvider,
        llm: BuildAnalyzer,
        max_log_characters: int = 10_000,
    ) -> None:
        self.jenkins = jenkins
        self.llm = llm
        self.max_log_characters = max_log_characters

    def execute(self, job: str, build: int) -> BuildAnalysis:
        log = self.jenkins.get_build_log(job, build)
        prompt = ANALYZE_BUILD_PROMPT.format(
            status="FAILURE",
            log=log[-self.max_log_characters :],
        )
        return self.llm.analyze(prompt)
