"""builds matched known error

Revision ID: bdcb1487656c
Revises: 934c32287d37
Create Date: 2026-07-02 10:54:03.607468

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdcb1487656c"
down_revision: str | Sequence[str] | None = "934c32287d37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE builds
        ADD COLUMN matched_known_error_id BIGINT
        REFERENCES known_errors (id) ON DELETE SET NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE builds DROP COLUMN IF EXISTS matched_known_error_id")
