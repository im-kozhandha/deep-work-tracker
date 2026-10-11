"""Initial schema exactly as supplied by the assessment.

Revision ID: 0001_initial_schema
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_CHECK_SQL = (
    "status IN ('scheduled', 'active', 'paused', 'completed', "
    "'interrupted', 'abandoned', 'overdue')"
)


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("scheduled_duration", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.TIMESTAMP(), nullable=True),
        sa.Column("end_time", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True, server_default="scheduled"),
        sa.Column(
            "created_at", sa.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.CheckConstraint(STATUS_CHECK_SQL),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "interruptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "pause_time", sa.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("interruptions")
    op.drop_table("sessions")