"""Add aluminum row to weld_thresholds.

Revision ID: 010_add_aluminum_threshold
Revises: 009_certifications
Create Date: 2026-02-23

Values from ALUMINUM_THRESHOLDS in threshold_service.py.
Stitch welding: wider angle/amps/volts/heat_diss for arc on/off variance.
"""

from alembic import op
import sqlalchemy as sa


revision = "010_add_aluminum_threshold"
down_revision = "009_certifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO weld_thresholds (weld_type, angle_target_degrees, angle_warning_margin, "
            "angle_critical_margin, thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius, "
            "amps_stability_warning, volts_stability_warning, heat_diss_consistency) "
            "VALUES ('aluminum', 45, 20, 35, 15, 35, 18, 25, 250)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM weld_thresholds WHERE weld_type = 'aluminum'"))
