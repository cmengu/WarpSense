"""drills and coaching_assignments tables

Revision ID: 008_coaching_drills
Revises: 007_session_annotations
Create Date: 2026-02-18
Owner: Batch 3 Agent 2
"""
from alembic import op
import sqlalchemy as sa

revision = "008_coaching_drills"
down_revision = "007_session_annotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drills",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("target_metric", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False,
                  server_default="3"),
        sa.Column("success_threshold", sa.Float, nullable=False,
                  server_default="70.0"),
    )
    op.create_table(
        "coaching_assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),
        sa.Column("drill_id", sa.Integer, sa.ForeignKey("drills.id"),
                  nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="active"),
        sa.Column("sessions_completed", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_coaching_assignments_welder_id",
                    "coaching_assignments", ["welder_id"])
    op.create_index("ix_coaching_assignments_status",
                    "coaching_assignments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_coaching_assignments_status", "coaching_assignments")
    op.drop_index("ix_coaching_assignments_welder_id", "coaching_assignments")
    op.drop_table("coaching_assignments")
    op.drop_table("drills")
