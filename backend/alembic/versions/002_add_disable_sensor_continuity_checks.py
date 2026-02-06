"""Add disable_sensor_continuity_checks to sessions."""

from alembic import op
import sqlalchemy as sa


revision = "002_disable_sensor_checks"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "disable_sensor_continuity_checks",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column(
        "sessions",
        "disable_sensor_continuity_checks",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("sessions", "disable_sensor_continuity_checks")
