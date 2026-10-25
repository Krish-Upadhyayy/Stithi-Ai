"""Initial database schema migration for SIH Training Centre AI Monitoring.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-07 19:45:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Centres table
    op.create_table(
        "centres",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_centres_centre_code"), "centres", ["centre_code"], unique=True)
    op.create_index(op.f("ix_centres_id"), "centres", ["id"], unique=False)

    # 2. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="CENTRE_USER"),
        sa.Column("centre_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # 3. Cameras table
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="VIDEO_FILE"),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cameras_id"), "cameras", ["id"], unique=False)

    # 4. Monitoring Sessions table
    op.create_table(
        "monitoring_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("camera_id", sa.Integer(), nullable=True),
        sa.Column("physical_attendance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_monitoring_sessions_id"), "monitoring_sessions", ["id"], unique=False)

    # 5. Snapshots table
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("monitoring_session_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("processing_status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["monitoring_session_id"], ["monitoring_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_snapshots_id"), "snapshots", ["id"], unique=False)

    # 6. Attendance Observations table (Anonymous presence, zero student identities)
    op.create_table(
        "attendance_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=False, server_default="YOLOv8-Face-Baseline"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attendance_observations_id"), "attendance_observations", ["id"], unique=False)

    # 7. Inventory Items table (Sanctioned baseline from Excel)
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("expected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_items_id"), "inventory_items", ["id"], unique=False)

    # 8. Infrastructure Observations table (Detected assets from separate YOLO)
    op.create_table(
        "infrastructure_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=True),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("detected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_version", sa.String(length=100), nullable=False, server_default="YOLO-Infra-Baseline"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_infrastructure_observations_id"), "infrastructure_observations", ["id"], unique=False)

    # 9. Alerts table (Discrepancy notices and evidence)
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False, server_default="MEDIUM"),
        sa.Column("expected_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observed_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("difference", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["monitoring_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("infrastructure_observations")
    op.drop_table("inventory_items")
    op.drop_table("attendance_observations")
    op.drop_table("snapshots")
    op.drop_table("monitoring_sessions")
    op.drop_table("cameras")
    op.drop_table("users")
    op.drop_table("centres")
