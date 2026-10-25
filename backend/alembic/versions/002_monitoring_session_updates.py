"""Monitoring session schema updates.

Revision ID: 002_monitoring_session_updates
Revises: 001_initial_schema
Create Date: 2026-10-07 21:40:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_monitoring_session_updates"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add session_date and created_by to monitoring_sessions
    with op.batch_alter_table("monitoring_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("session_date", sa.Date(), nullable=False, server_default=sa.func.current_date())
        )
        batch_op.add_column(
            sa.Column("created_by", sa.Integer(), nullable=True)
        )
        batch_op.alter_column(
            "started_at",
            existing_type=sa.DateTime(),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_monitoring_sessions_created_by",
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_monitoring_sessions_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("monitoring_sessions") as batch_op:
        batch_op.drop_index("ix_monitoring_sessions_status")
        batch_op.drop_constraint("fk_monitoring_sessions_created_by", type_="foreignkey")
        batch_op.alter_column(
            "started_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )
        batch_op.drop_column("created_by")
        batch_op.drop_column("session_date")
