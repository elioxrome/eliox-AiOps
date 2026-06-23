import requests
from pydantic import ValidationError

from src.application.errors import ExternalServiceError, InvalidLLMResponseError
from src.application.models import BuildAnalysis


class OllamaClient:
    def __init__(
        self,
        url: str,
        model: str = "qwen3:8b",
        timeout_seconds: float = 120.0,
        session: requests.Session | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def analyze(self, prompt: str) -> BuildAnalysis:
        try:
            response = self.session.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": 4_096,
                        "num_predict": 400,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = self._error_detail(exc.response)
            raise ExternalServiceError(f"Ollama request failed: {detail}") from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                f"Could not connect to Ollama at {self.url}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError("Ollama returned invalid JSON") from exc

        raw_analysis = payload.get("response")
        if not isinstance(raw_analysis, str):
            raise InvalidLLMResponseError(
                "Ollama response does not contain a textual 'response' field"
            )

        try:
            return BuildAnalysis.model_validate_json(raw_analysis)
        except ValidationError as exc:
            raise InvalidLLMResponseError(
                "Ollama response does not match the build analysis schema"
            ) from exc

    @staticmethod
    def _error_detail(response: requests.Response | None) -> str:
        if response is None:
            return "unknown HTTP error"

        try:
            payload = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"

        detail = payload.get("error")
        if isinstance(detail, str) and detail:
            return detail
        return f"HTTP {response.status_code}"
