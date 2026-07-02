import requests

from src.application.errors import ExternalServiceError, InvalidLLMResponseError


class OllamaEmbeddingClient:
    def __init__(
        self,
        url: str,
        model: str,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def embed(self, text: str) -> list[float]:
        try:
            response = self.session.post(
                f"{self.url}/api/embeddings",
                json={"model": self.model, "prompt": text},
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

        embedding = payload.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise InvalidLLMResponseError(
                "Ollama response does not contain an 'embedding' array"
            )
        return [float(value) for value in embedding]

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


class OpenAICompatibleEmbeddingClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def embed(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self.session.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"model": self.model, "input": text},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = self._error_detail(exc.response)
            raise ExternalServiceError(
                f"Embedding provider request failed: {detail}"
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                f"Could not connect to embedding provider at {self.base_url}"
            ) from exc

        try:
            payload = response.json()
            embedding = payload["data"][0]["embedding"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidLLMResponseError(
                "Embedding provider returned an invalid response"
            ) from exc

        if not isinstance(embedding, list) or not embedding:
            raise InvalidLLMResponseError(
                "Embedding provider response does not contain a vector"
            )
        return [float(value) for value in embedding]

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
