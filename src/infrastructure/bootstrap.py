"""Framework-agnostic wiring shared by the FastAPI process and the Celery
worker process. Each process gets its own per-process cache (`lru_cache`),
so a connection pool or client is created once per process, not once per
request/task.
"""

from functools import lru_cache

from psycopg_pool import ConnectionPool

from src.application.services.analysis_dispatcher import AnalysisDispatcher
from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.chat_with_build import ChatWithBuildUseCase
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.config import Settings
from src.infrastructure.jenkins.client import JenkinsClient
from src.infrastructure.llm.base import BuildAnalyzer, ChatClient, Embedder
from src.infrastructure.llm.factory import (
    create_build_analyzer,
    create_chat_model,
    create_embedder,
)
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.db import create_pool
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)
from src.infrastructure.queue.dispatcher import CeleryAnalysisDispatcher


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache
def get_pool() -> ConnectionPool:
    return create_pool(get_settings().database_url)


@lru_cache
def get_repository() -> BuildRepository:
    return BuildRepository(get_pool())


@lru_cache
def get_known_error_repository() -> KnownErrorRepository:
    return KnownErrorRepository(get_pool())


@lru_cache
def get_build_analyzer() -> BuildAnalyzer:
    return create_build_analyzer(get_settings())


@lru_cache
def get_embedder() -> Embedder:
    return create_embedder(get_settings())


@lru_cache
def get_chat_model() -> ChatClient:
    return create_chat_model(get_settings())


@lru_cache
def get_dispatcher() -> AnalysisDispatcher:
    return CeleryAnalysisDispatcher()


@lru_cache
def get_jenkins_client() -> JenkinsClient:
    settings = get_settings()
    return JenkinsClient(
        settings.jenkins_url,
        settings.jenkins_username,
        settings.jenkins_token,
        settings.jenkins_timeout_seconds,
    )


def get_ingest_use_case() -> IngestBuildUseCase:
    settings = get_settings()
    return IngestBuildUseCase(
        get_repository(),
        get_known_error_repository(),
        get_build_analyzer(),
        get_embedder(),
        get_dispatcher(),
        settings.max_log_characters,
        settings.rag_enabled,
        settings.rag_similarity_threshold,
    )


def get_jenkins_monitor() -> JenkinsMonitor:
    settings = get_settings()
    return JenkinsMonitor(
        get_jenkins_client(),
        get_repository(),
        get_ingest_use_case(),
        get_dispatcher(),
        settings.jenkins_poll_jobs,
        settings.jenkins_poll_interval_seconds,
    )


def get_chat_use_case() -> ChatWithBuildUseCase:
    return ChatWithBuildUseCase(
        get_repository(),
        get_chat_model(),
        get_settings().max_log_characters,
    )
