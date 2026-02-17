"""Add score_total to sessions for WWAD aggregate performance.

Revision ID: 003_add_score_total
Revises: 002_disable_sensor_checks
Create Date: 2025-02-17

"""

from alembic import op
import sqlalchemy as sa


revision = "003_add_score_total"
down_revision = "002_disable_sensor_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("score_total", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "score_total")
