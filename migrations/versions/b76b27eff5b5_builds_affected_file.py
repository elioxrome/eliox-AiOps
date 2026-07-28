"""builds affected file

Revision ID: b76b27eff5b5
Revises: 0871849c2c2e
Create Date: 2026-07-28 12:59:56.193472

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b76b27eff5b5"
down_revision: str | Sequence[str] | None = "0871849c2c2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE builds ADD COLUMN affected_file TEXT")
    op.execute("ALTER TABLE known_errors ADD COLUMN affected_file TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE builds DROP COLUMN IF EXISTS affected_file")
    op.execute("ALTER TABLE known_errors DROP COLUMN IF EXISTS affected_file")
