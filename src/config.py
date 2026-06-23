import os
from dataclasses import dataclass


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    jenkins_url: str
    jenkins_username: str | None
    jenkins_token: str | None
    jenkins_timeout_seconds: float
    llm_provider: str
    llm_base_url: str
    llm_model: str
    llm_api_key: str | None
    llm_timeout_seconds: float
    llm_temperature: float
    llm_context_tokens: int
    llm_max_output_tokens: int
    llm_json_mode: bool
    embedding_provider: str
    embedding_base_url: str
    embedding_model: str
    embedding_api_key: str | None
    embedding_timeout_seconds: float
    max_log_characters: int
    database_path: str
    ingestion_token: str | None
    dashboard_limit: int
    jenkins_poll_enabled: bool
    jenkins_poll_interval_seconds: int
    jenkins_poll_jobs: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            jenkins_url=os.getenv("JENKINS_URL", "http://jenkins:8080").rstrip("/"),
            jenkins_username=os.getenv("JENKINS_USERNAME") or None,
            jenkins_token=os.getenv("JENKINS_TOKEN") or None,
            jenkins_timeout_seconds=_positive_float(
                "JENKINS_TIMEOUT_SECONDS", 30.0
            ),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower(),
            llm_base_url=os.getenv(
                "LLM_BASE_URL",
                os.getenv("OLLAMA_URL", "http://ollama:11434"),
            ).rstrip("/"),
            llm_model=os.getenv(
                "LLM_MODEL",
                os.getenv("OLLAMA_MODEL", "qwen3:1.7b"),
            ),
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_timeout_seconds=_positive_float(
                "LLM_TIMEOUT_SECONDS",
                _positive_float("OLLAMA_TIMEOUT_SECONDS", 120.0),
            ),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            llm_context_tokens=_positive_int("LLM_CONTEXT_TOKENS", 4_096),
            llm_max_output_tokens=_positive_int("LLM_MAX_OUTPUT_TOKENS", 400),
            llm_json_mode=_boolean("LLM_JSON_MODE", True),
            embedding_provider=os.getenv(
                "EMBEDDING_PROVIDER",
                "ollama",
            ).strip().lower(),
            embedding_base_url=os.getenv(
                "EMBEDDING_BASE_URL",
                os.getenv("OLLAMA_URL", "http://ollama:11434"),
            ).rstrip("/"),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL",
                "embeddinggemma",
            ),
            embedding_api_key=os.getenv("EMBEDDING_API_KEY") or None,
            embedding_timeout_seconds=_positive_float(
                "EMBEDDING_TIMEOUT_SECONDS",
                60.0,
            ),
            max_log_characters=_positive_int("MAX_LOG_CHARACTERS", 4_000),
            database_path=os.getenv("DATABASE_PATH", "data/jenkins-aiops.db"),
            ingestion_token=os.getenv("INGESTION_TOKEN") or None,
            dashboard_limit=_positive_int("DASHBOARD_LIMIT", 100),
            jenkins_poll_enabled=_boolean("JENKINS_POLL_ENABLED", False),
            jenkins_poll_interval_seconds=_positive_int(
                "JENKINS_POLL_INTERVAL_SECONDS",
                15,
            ),
            jenkins_poll_jobs=tuple(
                job.strip()
                for job in os.getenv("JENKINS_POLL_JOBS", "*").split(",")
                if job.strip()
            ),
        )
