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


@dataclass(frozen=True)
class FrontendSettings:
    api_base_url: str
    request_timeout_seconds: float
    dashboard_limit: int

    @classmethod
    def from_env(cls) -> "FrontendSettings":
        return cls(
            api_base_url=os.getenv(
                "API_BASE_URL", "http://127.0.0.1:8000"
            ).rstrip("/"),
            # Chat is synchronous end-to-end; must stay above the backend's
            # LLM_TIMEOUT_SECONDS (120s default) or the frontend gives up
            # while the API is still waiting on the LLM.
            request_timeout_seconds=_positive_float(
                "API_REQUEST_TIMEOUT_SECONDS", 130.0
            ),
            dashboard_limit=_positive_int("DASHBOARD_LIMIT", 100),
        )
