"""Initial schema for canonical time-series sessions.
This script sets up the database for your welding sessions, ensuring every session and frame is stored with proper constraints, indexes, and JSON fields. It's the backbone for your ORM + Pydantic models to persist and validate data.

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("operator_id", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weld_type", sa.String(), nullable=False),
        sa.Column("thermal_sample_interval_ms", sa.Integer(), nullable=False),
        sa.Column("thermal_directions", postgresql.JSONB(), nullable=False),
        sa.Column("thermal_distance_interval_mm", sa.Float(), nullable=False),
        sa.Column("sensor_sample_rate_hz", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="recording"),
        sa.Column("frame_count", sa.Integer(), nullable=False),
        sa.Column("expected_frame_count", sa.Integer(), nullable=True),
        sa.Column("last_successful_frame_index", sa.Integer(), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('recording','incomplete','complete','failed','archived')",
            name="ck_sessions_status",
        ),
    )

    op.create_index("idx_sessions_operator_id", "sessions", ["operator_id"])
    op.create_index("idx_sessions_start_time", "sessions", ["start_time"])
    op.create_index("idx_sessions_weld_type", "sessions", ["weld_type"])

    op.create_table(
        "frames",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("frame_data", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            ondelete="CASCADE",
            name="fk_frames_session_id",
        ),
        sa.CheckConstraint("timestamp_ms >= 0", name="ck_frames_timestamp_nonnegative"),
        sa.UniqueConstraint("session_id", "timestamp_ms", name="uq_frames_session_timestamp"),
    )

    op.create_index(
        "idx_frames_session_timestamp",
        "frames",
        ["session_id", sa.text("timestamp_ms DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_frames_session_timestamp", table_name="frames")
    op.drop_table("frames")
    op.drop_index("idx_sessions_weld_type", table_name="sessions")
    op.drop_index("idx_sessions_start_time", table_name="sessions")
    op.drop_index("idx_sessions_operator_id", table_name="sessions")
    op.drop_table("sessions")
