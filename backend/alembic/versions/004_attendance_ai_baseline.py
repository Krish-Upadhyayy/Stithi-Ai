"""Attendance AI baseline schema updates.

Revision ID: 004_attendance_ai_baseline
Revises: 003_video_and_snapshot_engine
Create Date: 2026-10-07 23:15:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_attendance_ai_baseline"
down_revision: Union[str, None] = "003_video_and_snapshot_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("attendance_observations") as batch_op:
        batch_op.add_column(sa.Column("monitoring_session_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("min_confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("max_confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("confidence_threshold", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("model_name", sa.String(length=100), nullable=False, server_default="YOLO26-Face-Presence"))
        batch_op.add_column(sa.Column("inference_time_ms", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("inference_device", sa.String(length=50), nullable=True, server_default="cpu"))
        batch_op.add_column(sa.Column("processing_status", sa.String(length=50), nullable=False, server_default="COMPLETED"))
        batch_op.add_column(sa.Column("annotated_image_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("detection_metadata", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_attendance_observations_session",
            "monitoring_sessions",
            ["monitoring_session_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_attendance_observations_session_id", ["monitoring_session_id"])
        batch_op.create_index("ix_attendance_observations_processing_status", ["processing_status"])


def downgrade() -> None:
    with op.batch_alter_table("attendance_observations") as batch_op:
        batch_op.drop_index("ix_attendance_observations_processing_status")
        batch_op.drop_index("ix_attendance_observations_session_id")
        batch_op.drop_constraint("fk_attendance_observations_session", type_="foreignkey")
        batch_op.drop_column("detection_metadata")
        batch_op.drop_column("annotated_image_path")
        batch_op.drop_column("processing_status")
        batch_op.drop_column("inference_device")
        batch_op.drop_column("inference_time_ms")
        batch_op.drop_column("model_name")
        batch_op.drop_column("confidence_threshold")
        batch_op.drop_column("max_confidence")
        batch_op.drop_column("min_confidence")
        batch_op.drop_column("monitoring_session_id")
