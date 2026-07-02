"""chat messages

Revision ID: 0871849c2c2e
Revises: bdcb1487656c
Create Date: 2026-07-02 10:54:03.865703

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0871849c2c2e"
down_revision: str | Sequence[str] | None = "bdcb1487656c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE build_chat_messages (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            build_id BIGINT NOT NULL REFERENCES builds (id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX build_chat_messages_build_id_idx
        ON build_chat_messages (build_id, created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS build_chat_messages")
