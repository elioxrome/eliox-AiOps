"""initial schema

Revision ID: ab1386998fbf
Revises:
Create Date: 2026-07-02 10:54:03.090919

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab1386998fbf"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE builds (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            job_name TEXT NOT NULL,
            build_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            build_url TEXT,
            log TEXT NOT NULL,
            processing_status TEXT NOT NULL,
            category TEXT,
            root_cause TEXT,
            confidence DOUBLE PRECISION,
            recommendation TEXT,
            error TEXT,
            rating INTEGER,
            feedback_comment TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            UNIQUE (job_name, build_number)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE monitor_state (
            job_name TEXT PRIMARY KEY,
            last_build_number INTEGER NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monitor_state")
    op.execute("DROP TABLE IF EXISTS builds")
