"""Video and snapshot engine schema updates.

Revision ID: 003_video_and_snapshot_engine
Revises: 002_monitoring_session_updates
Create Date: 2026-10-07 22:33:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_video_and_snapshot_engine"
down_revision: Union[str, None] = "002_monitoring_session_updates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update monitoring_sessions with video metadata columns
    with op.batch_alter_table("monitoring_sessions") as batch_op:
        batch_op.add_column(sa.Column("video_file_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("video_filename", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("video_file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("video_duration_seconds", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("video_fps", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("video_width", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("video_height", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("video_total_frames", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("video_processing_status", sa.String(length=50), nullable=False, server_default="NOT_STARTED"))
        batch_op.add_column(sa.Column("video_error_message", sa.String(length=500), nullable=True))
        batch_op.create_index("ix_monitoring_sessions_video_processing_status", ["video_processing_status"], unique=False)

    # 2. Update snapshots with dimensional and frame time metadata
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.add_column(sa.Column("frame_time_seconds", sa.Float(), nullable=True, server_default="0.0"))
        batch_op.add_column(sa.Column("width", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("height", sa.Integer(), nullable=True))
        batch_op.create_index("ix_snapshots_processing_status", ["processing_status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.drop_index("ix_snapshots_processing_status")
        batch_op.drop_column("height")
        batch_op.drop_column("width")
        batch_op.drop_column("frame_time_seconds")

    with op.batch_alter_table("monitoring_sessions") as batch_op:
        batch_op.drop_index("ix_monitoring_sessions_video_processing_status")
        batch_op.drop_column("video_error_message")
        batch_op.drop_column("video_processing_status")
        batch_op.drop_column("video_total_frames")
        batch_op.drop_column("video_height")
        batch_op.drop_column("video_width")
        batch_op.drop_column("video_fps")
        batch_op.drop_column("video_duration_seconds")
        batch_op.drop_column("video_file_size")
        batch_op.drop_column("video_filename")
        batch_op.drop_column("video_file_path")
