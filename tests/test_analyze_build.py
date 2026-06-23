from src.application.models import BuildAnalysis
from src.application.use_cases.analyze_build import AnalyzeBuildUseCase


class FakeJenkins:
    def get_build_log(self, job_name: str, build_number: int) -> str:
        assert job_name == "deploy"
        assert build_number == 42
        return "prefix-important failure"


class FakeLLM:
    prompt: str

    def analyze(self, prompt: str) -> BuildAnalysis:
        self.prompt = prompt
        return BuildAnalysis(
            category="deployment",
            root_cause="Image pull failed",
            confidence=0.9,
            recommendation="Check registry credentials",
        )


def test_analyzes_the_tail_of_the_build_log() -> None:
    llm = FakeLLM()
    use_case = AnalyzeBuildUseCase(FakeJenkins(), llm, max_log_characters=17)

    result = use_case.execute("deploy", 42)

    assert result.category == "deployment"
    assert "important failure" in llm.prompt
    assert "prefix-" not in llm.prompt
    assert "Responde siempre en español" in llm.prompt
