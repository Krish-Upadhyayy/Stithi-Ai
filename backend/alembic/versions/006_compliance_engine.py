"""Compliance Engine schema updates.

Revision ID: 006_compliance_engine
Revises: 005_infrastructure_ai_updates
Create Date: 2026-10-08 02:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006_compliance_engine"
down_revision: Union[str, None] = "005_infrastructure_ai_updates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Attendance compliance results table
    op.create_table(
        "attendance_compliance_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("monitoring_session_id", sa.Integer(), nullable=False),
        sa.Column("physical_attendance", sa.Integer(), nullable=False),
        sa.Column("ai_estimated_attendance", sa.Float(), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.Column("tolerance", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("aggregation_method", sa.String(length=50), nullable=False, server_default="MEDIAN"),
        sa.Column("valid_observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_snapshots_considered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitoring_session_id"], ["monitoring_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitoring_session_id"),
    )
    op.create_index(
        "ix_attendance_compliance_results_monitoring_session_id",
        "attendance_compliance_results",
        ["monitoring_session_id"],
        unique=True,
    )
    op.create_index(
        "ix_attendance_compliance_results_status",
        "attendance_compliance_results",
        ["status"],
        unique=False,
    )

    # 2. Infrastructure compliance results table
    op.create_table(
        "infrastructure_compliance_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("monitoring_session_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=True),
        sa.Column("item_name", sa.String(length=150), nullable=False),
        sa.Column("ai_class", sa.String(length=100), nullable=True),
        sa.Column("expected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observed_quantity", sa.Float(), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.Column("aggregation_method", sa.String(length=50), nullable=False, server_default="MEDIAN"),
        sa.Column("valid_observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_snapshots_considered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitoring_session_id"], ["monitoring_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_infrastructure_compliance_results_monitoring_session_id",
        "infrastructure_compliance_results",
        ["monitoring_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_infrastructure_compliance_results_inventory_item_id",
        "infrastructure_compliance_results",
        ["inventory_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_infrastructure_compliance_results_status",
        "infrastructure_compliance_results",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_infrastructure_compliance_results_status", table_name="infrastructure_compliance_results")
    op.drop_index("ix_infrastructure_compliance_results_inventory_item_id", table_name="infrastructure_compliance_results")
    op.drop_index("ix_infrastructure_compliance_results_monitoring_session_id", table_name="infrastructure_compliance_results")
    op.drop_table("infrastructure_compliance_results")

    op.drop_index("ix_attendance_compliance_results_status", table_name="attendance_compliance_results")
    op.drop_index("ix_attendance_compliance_results_monitoring_session_id", table_name="attendance_compliance_results")
    op.drop_table("attendance_compliance_results")
