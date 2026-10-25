"""Dashboard query performance indexes.

Revision ID: 008_dashboard_indexes
Revises: 007_alerts_and_evidence
Create Date: 2026-10-08 02:30:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008_dashboard_indexes"
down_revision: Union[str, None] = "007_alerts_and_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely create indexes if not already present
    try:
        with op.batch_alter_table("monitoring_sessions") as batch_op:
            batch_op.create_index("ix_monitoring_sessions_created_at", ["created_at"], unique=False)
    except Exception:
        pass

    try:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.create_index("ix_alerts_created_at", ["created_at"], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    try:
        with op.batch_alter_table("monitoring_sessions") as batch_op:
            batch_op.drop_index("ix_monitoring_sessions_created_at")
    except Exception:
        pass

    try:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.drop_index("ix_alerts_created_at")
    except Exception:
        pass
