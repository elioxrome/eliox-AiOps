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
    ollama_url: str
    ollama_model: str
    ollama_timeout_seconds: float
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
            ollama_url=os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            ollama_timeout_seconds=_positive_float("OLLAMA_TIMEOUT_SECONDS", 120.0),
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
