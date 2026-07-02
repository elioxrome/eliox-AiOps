from src.config import Settings
from src.infrastructure.llm.base import BuildAnalyzer, ChatClient, Embedder
from src.infrastructure.llm.embedding_client import (
    OllamaEmbeddingClient,
    OpenAICompatibleEmbeddingClient,
)
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


def create_chat_model(settings: Settings) -> ChatClient:
    # The chat feature reuses the generation provider/model: it is a
    # conversation about the same build, not a separate capability.
    return create_build_analyzer(settings)


def create_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingClient(
            settings.embedding_base_url,
            settings.embedding_model,
            settings.embedding_timeout_seconds,
        )

    if settings.embedding_provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleEmbeddingClient(
            settings.embedding_base_url,
            settings.embedding_model,
            settings.embedding_api_key,
            settings.embedding_timeout_seconds,
        )

    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}"
    )
