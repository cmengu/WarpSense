"""Populate aluminum row with Step 8 calibration values.

Revision ID: 013_populate_aluminum_feature_thresholds
Revises: 012_add_aluminum_feature_columns
Create Date: 2026-02-23

Values from Step 8 calibration (30 sessions):
- travel_speed_consistency: 67.68 (expert p95=43.26, novice p5=92.10, suggested midpoint)
- cyclogram_area_max: 16.21 (expert p95=7.89, novice p5=24.52, suggested midpoint)
- porosity_event_max: 7.5 (expert p95=4, novice p5=11, suggested midpoint)
"""

from alembic import op
import sqlalchemy as sa


revision = "013_al_feat_thresholds"
down_revision = "012_add_aluminum_feature_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE weld_thresholds
            SET
                travel_speed_consistency = 67.68,
                cyclogram_area_max       = 16.21,
                porosity_event_max       = 7.5
            WHERE weld_type = 'aluminum'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE weld_thresholds
            SET
                travel_speed_consistency = NULL,
                cyclogram_area_max       = NULL,
                porosity_event_max       = NULL
            WHERE weld_type = 'aluminum'
            """
        )
    )
