from src.application.services.jenkins_monitor import JenkinsMonitor
from src.application.use_cases.chat_with_build import ChatWithBuildUseCase
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.config import Settings
from src.infrastructure import bootstrap
from src.infrastructure.llm.base import BuildAnalyzer
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)


def get_settings() -> Settings:
    return bootstrap.get_settings()


def get_repository() -> BuildRepository:
    return bootstrap.get_repository()


def get_known_error_repository() -> KnownErrorRepository:
    return bootstrap.get_known_error_repository()


def get_build_analyzer() -> BuildAnalyzer:
    return bootstrap.get_build_analyzer()


def get_ingest_use_case() -> IngestBuildUseCase:
    return bootstrap.get_ingest_use_case()


def get_jenkins_monitor() -> JenkinsMonitor:
    return bootstrap.get_jenkins_monitor()


def get_chat_use_case() -> ChatWithBuildUseCase:
    return bootstrap.get_chat_use_case()
