"""known errors

Revision ID: 934c32287d37
Revises: ab1386998fbf
Create Date: 2026-07-02 10:54:03.347858

"""
from collections.abc import Sequence

from alembic import op

from src.config import Settings

# revision identifiers, used by Alembic.
revision: str = "934c32287d37"
down_revision: str | Sequence[str] | None = "ab1386998fbf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dimensions = Settings.from_env().embedding_dimensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE known_errors (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            signature TEXT NOT NULL,
            embedding VECTOR({dimensions}) NOT NULL,
            category TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            trust_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            hit_count INTEGER NOT NULL DEFAULT 0,
            last_matched_at TIMESTAMPTZ,
            source_build_id BIGINT REFERENCES builds (id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX known_errors_embedding_hnsw_idx
        ON known_errors USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS known_errors")
