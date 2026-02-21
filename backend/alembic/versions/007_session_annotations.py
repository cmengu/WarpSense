"""session_annotations table

Revision ID: 007_session_annotations
Revises: 006_session_narratives
Create Date: 2026-02-18
Owner: Batch 2 Agent 2
"""
from alembic import op
import sqlalchemy as sa

revision = "007_session_annotations"
down_revision = "006_session_narratives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_annotations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp_ms", sa.BigInteger, nullable=False),
        sa.Column("annotation_type", sa.String(32), nullable=False),
        # Values: defect_confirmed | near_miss | technique_error | equipment_issue
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_session_annotations_session_id", "session_annotations", ["session_id"]
    )
    op.create_index(
        "ix_session_annotations_type", "session_annotations", ["annotation_type"]
    )
    op.create_index(
        "ix_session_annotations_type_created",
        "session_annotations",
        ["annotation_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_annotations_type_created", "session_annotations")
    op.drop_index("ix_session_annotations_type", "session_annotations")
    op.drop_index("ix_session_annotations_session_id", "session_annotations")
    op.drop_table("session_annotations")
