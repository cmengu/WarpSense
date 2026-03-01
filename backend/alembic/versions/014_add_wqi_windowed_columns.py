"""Add windowed WQI columns to sessions.

Revision ID: 014_add_wqi_windowed_columns
Revises: 013_al_feat_thresholds
Create Date: 2026-03-01

Adds wqi_timeline, mean_wqi, median_wqi, min_wqi, max_wqi, wqi_trend for
windowed WQI scoring (50-frame tumbling windows).
"""

from alembic import op
import sqlalchemy as sa


revision = "014_add_wqi_windowed_columns"
down_revision = "013_al_feat_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("wqi_timeline", sa.JSON(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("mean_wqi", sa.Float(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("median_wqi", sa.Float(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("min_wqi", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("max_wqi", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("wqi_trend", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "wqi_trend")
    op.drop_column("sessions", "max_wqi")
    op.drop_column("sessions", "min_wqi")
    op.drop_column("sessions", "median_wqi")
    op.drop_column("sessions", "mean_wqi")
    op.drop_column("sessions", "wqi_timeline")
