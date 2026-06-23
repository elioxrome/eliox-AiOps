import requests
from pydantic import ValidationError

from src.application.errors import ExternalServiceError, InvalidLLMResponseError
from src.application.models import BuildAnalysis


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
        temperature: float = 0.1,
        max_output_tokens: int = 400,
        json_mode: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.json_mode = json_mode
        self.session = session or requests.Session()

    def analyze(self, prompt: str) -> BuildAnalysis:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            request_body = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_output_tokens,
            }
            if self.json_mode:
                request_body["response_format"] = {"type": "json_object"}

            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = self._error_detail(exc.response)
            raise ExternalServiceError(
                f"LLM provider request failed: {detail}"
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                f"Could not connect to LLM provider at {self.base_url}"
            ) from exc

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidLLMResponseError(
                "LLM provider returned an invalid chat completion"
            ) from exc

        if not isinstance(content, str):
            raise InvalidLLMResponseError(
                "LLM provider response content is not text"
            )

        try:
            return BuildAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise InvalidLLMResponseError(
                "LLM provider response does not match the analysis schema"
            ) from exc

    @staticmethod
    def _error_detail(response: requests.Response | None) -> str:
        if response is None:
            return "unknown HTTP error"
        try:
            payload = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"

        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        if isinstance(error, str):
            return error
        return f"HTTP {response.status_code}"
