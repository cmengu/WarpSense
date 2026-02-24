"""Add travel_speed_consistency, cyclogram_area_max, porosity_event_max to weld_thresholds.

Revision ID: 012_add_aluminum_feature_columns
Revises: 011_adjust_aluminum_thresholds
Create Date: 2026-02-23

Schema only. Migration B will populate aluminum row with Step 8 calibration values.
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_aluminum_feature_columns"
down_revision = "011_adjust_aluminum_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "weld_thresholds",
        sa.Column("travel_speed_consistency", sa.Float(), nullable=True),
    )
    op.add_column(
        "weld_thresholds",
        sa.Column("cyclogram_area_max", sa.Float(), nullable=True),
    )
    op.add_column(
        "weld_thresholds",
        sa.Column("porosity_event_max", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("weld_thresholds", "porosity_event_max")
    op.drop_column("weld_thresholds", "cyclogram_area_max")
    op.drop_column("weld_thresholds", "travel_speed_consistency")
