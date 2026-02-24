"""cert_standards and welder_certifications tables

Revision ID: 009_certifications
Revises: 008_coaching_drills
Create Date: 2026-02-18
Owner: Batch 3 Agent 3
"""
from alembic import op
import sqlalchemy as sa

revision = "009_certifications"
down_revision = "008_coaching_drills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cert_standards",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("required_score", sa.Float, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False),
        sa.Column("weld_type", sa.String(32), nullable=True),
    )
    op.create_table(
        "welder_certifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),
        sa.Column("cert_standard_id", sa.String(32),
                  sa.ForeignKey("cert_standards.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="not_started"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("qualifying_session_ids", sa.JSON, nullable=True),
        sa.UniqueConstraint("welder_id", "cert_standard_id",
                            name="uq_welder_cert"),
    )
    op.create_index("ix_welder_certifications_welder_id",
                    "welder_certifications", ["welder_id"])


def downgrade() -> None:
    op.drop_index("ix_welder_certifications_welder_id",
                  "welder_certifications")
    op.drop_table("welder_certifications")
    op.drop_table("cert_standards")
