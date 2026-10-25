"""Alerts and Evidence schema updates.

Revision ID: 007_alerts_and_evidence
Revises: 006_compliance_engine
Create Date: 2026-10-08 02:10:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007_alerts_and_evidence"
down_revision: Union[str, None] = "006_compliance_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add fields to alerts table
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(sa.Column("monitoring_session_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(length=200), nullable=False, server_default="Potential Discrepancy Detected"))
        batch_op.add_column(sa.Column("compliance_result_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("inventory_item_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("detected_value", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("reviewed_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("reviewer_comment", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_alerts_monitoring_session_id", "monitoring_sessions", ["monitoring_session_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_alerts_inventory_item_id", "inventory_items", ["inventory_item_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            "fk_alerts_reviewed_by", "users", ["reviewed_by"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index("ix_alerts_monitoring_session_id", ["monitoring_session_id"])
        batch_op.create_index("ix_alerts_alert_type", ["alert_type"])
        batch_op.create_index("ix_alerts_severity", ["severity"])
        batch_op.create_index("ix_alerts_status", ["status"])

    # 2. Create alert_evidence table
    op.create_table(
        "alert_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_evidence_alert_id", "alert_evidence", ["alert_id"], unique=False)
    op.create_index("ix_alert_evidence_snapshot_id", "alert_evidence", ["snapshot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_evidence_snapshot_id", table_name="alert_evidence")
    op.drop_index("ix_alert_evidence_alert_id", table_name="alert_evidence")
    op.drop_table("alert_evidence")

    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_index("ix_alerts_status")
        batch_op.drop_index("ix_alerts_severity")
        batch_op.drop_index("ix_alerts_alert_type")
        batch_op.drop_index("ix_alerts_monitoring_session_id")
        batch_op.drop_constraint("fk_alerts_reviewed_by", type_="foreignkey")
        batch_op.drop_constraint("fk_alerts_inventory_item_id", type_="foreignkey")
        batch_op.drop_constraint("fk_alerts_monitoring_session_id", type_="foreignkey")
        batch_op.drop_column("reviewer_comment")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("detected_value")
        batch_op.drop_column("inventory_item_id")
        batch_op.drop_column("compliance_result_id")
        batch_op.drop_column("title")
        batch_op.drop_column("monitoring_session_id")
