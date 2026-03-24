"""add rework_cost_usd to weld_quality_reports

Revision ID: 015_add_rework_cost_usd
Revises: d7f5691965bf
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015_add_rework_cost_usd"
down_revision: Union[str, Sequence[str], None] = "d7f5691965bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "weld_quality_reports",
        sa.Column("rework_cost_usd", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("weld_quality_reports", "rework_cost_usd")
