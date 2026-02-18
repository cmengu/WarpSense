"""sites and teams tables, nullable team_id on sessions

Revision ID: 005_sites_teams
Revises: 004_weld_thresholds_process_type
Create Date: 2026-02-18
Owner: Batch 1 Agent 1
"""
from alembic import op
import sqlalchemy as sa

revision = "005_sites_teams"
down_revision = "004_weld_thresholds_process_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sites ──────────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── teams ───────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "site_id",
            sa.String(64),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_teams_site_id", "teams", ["site_id"])

    # ── sessions.team_id — nullable FK, zero data impact ──────────────────
    op.add_column(
        "sessions",
        sa.Column(
            "team_id",
            sa.String(64),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_sessions_team_id", "sessions", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_team_id", table_name="sessions")
    op.drop_column("sessions", "team_id")
    op.drop_index("ix_teams_site_id", table_name="teams")
    op.drop_table("teams")
    op.drop_table("sites")
