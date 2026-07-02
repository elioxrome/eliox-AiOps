import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from psycopg_pool import ConnectionPool
from testcontainers.postgres import PostgresContainer

from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.db import create_pool
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def _database_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as container:
        url = container.get_connection_url().replace(
            "postgresql+psycopg://", "postgresql://"
        )
        os.environ["DATABASE_URL"] = url
        os.environ.setdefault("EMBEDDING_DIMENSIONS", "8")

        alembic_cfg = Config(str(_REPO_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option(
            "script_location", str(_REPO_ROOT / "migrations")
        )
        command.upgrade(alembic_cfg, "head")

        yield url


@pytest.fixture(scope="session")
def _pool(_database_url: str) -> Iterator[ConnectionPool]:
    pool = create_pool(_database_url)
    yield pool
    pool.close()


@pytest.fixture
def db_pool(_pool: ConnectionPool) -> ConnectionPool:
    with _pool.connection() as connection:
        connection.execute(
            """
            TRUNCATE build_chat_messages, known_errors, monitor_state, builds
            RESTART IDENTITY CASCADE
            """
        )
    return _pool


@pytest.fixture
def repository(db_pool: ConnectionPool) -> BuildRepository:
    return BuildRepository(db_pool)


@pytest.fixture
def known_error_repository(db_pool: ConnectionPool) -> KnownErrorRepository:
    return KnownErrorRepository(db_pool)
