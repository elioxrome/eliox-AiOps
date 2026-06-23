from functools import lru_cache

from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.config import Settings
from src.infrastructure.jenkins.client import JenkinsClient
from src.infrastructure.llm.base import BuildAnalyzer
from src.infrastructure.llm.factory import create_build_analyzer
from src.infrastructure.persistence.build_repository import BuildRepository


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache
def get_repository() -> BuildRepository:
    repository = BuildRepository(get_settings().database_path)
    repository.initialize()
    return repository


def get_build_analyzer() -> BuildAnalyzer:
    return create_build_analyzer(get_settings())


def get_jenkins_monitor() -> JenkinsMonitor:
    settings = get_settings()
    repository = get_repository()
    ingestion = IngestBuildUseCase(
        repository,
        get_build_analyzer(),
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
