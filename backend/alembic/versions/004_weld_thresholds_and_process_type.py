"""Add weld_thresholds table and process_type to sessions.

Revision ID: 004_weld_thresholds_process_type
Revises: 003_add_score_total
Create Date: 2025-02-18

"""

from alembic import op
import sqlalchemy as sa


revision = "004_weld_thresholds_process_type"
down_revision = "003_add_score_total"
branch_labels = None
depends_on = None

SEED_DATA = [
    ("mig", 45, 5, 15, 60, 80, 5, 1, 40),
    ("tig", 75, 10, 20, 60, 80, 5, 1, 40),
    ("stick", 20, 8, 20, 60, 80, 5, 1, 40),
    ("flux_core", 45, 7, 18, 60, 80, 5, 1, 40),
]


def upgrade() -> None:
    # Add process_type to sessions
    op.add_column(
        "sessions",
        sa.Column("process_type", sa.String(), nullable=True),
    )
    # Backfill process_type: single UPDATE for typical DBs; for 100k+ rows use batched variant
    op.execute(
        sa.text("UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL")
    )
    op.alter_column(
        "sessions",
        "process_type",
        nullable=False,
        server_default="mig",
    )
    op.create_index("idx_sessions_process_type", "sessions", ["process_type"])

    # Create weld_thresholds
    op.create_table(
        "weld_thresholds",
        sa.Column("weld_type", sa.String(), primary_key=True),
        sa.Column("angle_target_degrees", sa.Float(), nullable=False),
        sa.Column("angle_warning_margin", sa.Float(), nullable=False),
        sa.Column("angle_critical_margin", sa.Float(), nullable=False),
        sa.Column("thermal_symmetry_warning_celsius", sa.Float(), nullable=False),
        sa.Column("thermal_symmetry_critical_celsius", sa.Float(), nullable=False),
        sa.Column("amps_stability_warning", sa.Float(), nullable=False),
        sa.Column("volts_stability_warning", sa.Float(), nullable=False),
        sa.Column("heat_diss_consistency", sa.Float(), nullable=False),
    )
    for row in SEED_DATA:
        op.execute(
            sa.text(
                "INSERT INTO weld_thresholds (weld_type, angle_target_degrees, "
                "angle_warning_margin, angle_critical_margin, "
                "thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius, "
                "amps_stability_warning, volts_stability_warning, heat_diss_consistency) "
                "VALUES (:w, :a, :aw, :ac, :tw, :tc, :amps, :volts, :hd)"
            ).bindparams(
                w=row[0],
                a=row[1],
                aw=row[2],
                ac=row[3],
                tw=row[4],
                tc=row[5],
                amps=row[6],
                volts=row[7],
                hd=row[8],
            )
        )


def downgrade() -> None:
    op.drop_table("weld_thresholds")
    op.drop_index("idx_sessions_process_type", table_name="sessions")
    op.drop_column("sessions", "process_type")
