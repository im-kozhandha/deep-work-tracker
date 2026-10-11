"""Add interruptions.resume_time, a session_id index and a one-open-pause-per-session guard.

Revision ID: 0002_interruption_resume_time
Revises: 0001_initial_schema
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_interruption_resume_time"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("interruptions", sa.Column("resume_time", sa.TIMESTAMP(), nullable=True))
    op.create_index("ix_interruptions_session_id", "interruptions", ["session_id"])
    op.create_index(
        "uq_interruptions_one_open_pause",
        "interruptions",
        ["session_id"],
        unique=True,
        sqlite_where=sa.text("resume_time IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_interruptions_one_open_pause", table_name="interruptions")
    op.drop_index("ix_interruptions_session_id", table_name="interruptions")
    with op.batch_alter_table("interruptions") as batch_op:
        batch_op.drop_column("resume_time")