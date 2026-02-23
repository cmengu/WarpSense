"""Adjust aluminum thresholds: amps 75 (stitch variance), thermal 9 (novice discriminator).

Revision ID: 011_adjust_aluminum_thresholds
Revises: 010_add_aluminum_threshold
Create Date: 2026-02-23

Expert amps_stddev ~71 (0 vs ~145); novice thermal 9.59.
"""

from alembic import op
import sqlalchemy as sa


revision = "011_adjust_aluminum_thresholds"
down_revision = "010_add_aluminum_threshold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE weld_thresholds SET amps_stability_warning = 75, "
            "thermal_symmetry_warning_celsius = 9 WHERE weld_type = 'aluminum'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE weld_thresholds SET amps_stability_warning = 18, "
            "thermal_symmetry_warning_celsius = 15 WHERE weld_type = 'aluminum'"
        )
    )
