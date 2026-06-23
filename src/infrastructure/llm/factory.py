from src.config import Settings
from src.infrastructure.llm.base import BuildAnalyzer
from src.infrastructure.llm.ollama_client import OllamaClient
from src.infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)


def create_build_analyzer(settings: Settings) -> BuildAnalyzer:
    if settings.llm_provider == "ollama":
        return OllamaClient(
            settings.llm_base_url,
            settings.llm_model,
            settings.llm_timeout_seconds,
            settings.llm_temperature,
            settings.llm_context_tokens,
            settings.llm_max_output_tokens,
        )

    if settings.llm_provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleClient(
            settings.llm_base_url,
            settings.llm_model,
            settings.llm_api_key,
            settings.llm_timeout_seconds,
            settings.llm_temperature,
            settings.llm_max_output_tokens,
            settings.llm_json_mode,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {settings.llm_provider}"
    )
