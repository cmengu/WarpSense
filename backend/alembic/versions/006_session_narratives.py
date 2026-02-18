"""session_narratives cache table

Revision ID: 006_session_narratives
Revises: 005_sites_teams
Create Date: 2026-02-18
Owner: Batch 1 Agent 3
"""
from alembic import op
import sqlalchemy as sa

revision = "006_session_narratives"
down_revision = "005_sites_teams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_narratives",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("narrative_text", sa.Text, nullable=False),
        sa.Column("score_snapshot", sa.Float, nullable=True),
        sa.Column(
            "model_version",
            sa.String(64),
            nullable=False,
            server_default="claude-sonnet-4-6",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_session_narratives_session_id", "session_narratives", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_session_narratives_session_id", "session_narratives")
    op.drop_table("session_narratives")
