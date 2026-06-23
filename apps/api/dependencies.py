from functools import lru_cache

from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.config import Settings
from src.infrastructure.jenkins.client import JenkinsClient
from src.infrastructure.llm.ollama_client import OllamaClient
from src.infrastructure.persistence.build_repository import BuildRepository


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache
def get_repository() -> BuildRepository:
    repository = BuildRepository(get_settings().database_path)
    repository.initialize()
    return repository


def get_ollama_client() -> OllamaClient:
    settings = get_settings()
    return OllamaClient(
        settings.ollama_url,
        settings.ollama_model,
        settings.ollama_timeout_seconds,
    )


def get_jenkins_monitor() -> JenkinsMonitor:
    settings = get_settings()
    repository = get_repository()
    ingestion = IngestBuildUseCase(
        repository,
        get_ollama_client(),
        settings.max_log_characters,
    )
    jenkins = JenkinsClient(
        settings.jenkins_url,
        settings.jenkins_username,
        settings.jenkins_token,
        settings.jenkins_timeout_seconds,
    )
    return JenkinsMonitor(
        jenkins,
        repository,
        ingestion,
        settings.jenkins_poll_jobs,
        settings.jenkins_poll_interval_seconds,
    )
