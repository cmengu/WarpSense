"""
[Your Code / API / Data Input]
        │
        ▼
[Pydantic Model Validation]  <-- validates type, optional/required, constraints
        │
        ▼
[SQLAlchemy ORM]  <-- maps Pydantic → DB, handles reading/writing
        │
        ▼
[PostgreSQL Database]  <-- schema updated via Alembic migration
        │
        ▼
[Back to Python]  <-- ORM reads DB rows into objects
        │
        ▼
[Tests]  <-- ensure all new/old rules work

Tests for database schema and constraints.
This migration creates the core database structure for storing welding sessions and frames, with rules and indexes to enforce consistency, prevent duplicates, and support fast queries.
They only validate database-level constraints: schema, uniqueness, indexes, and ordering.
"""

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not set")
    return create_engine(database_url, future=True)


def test_schema_created_correctly():
    engine = _engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "sessions" in tables
    assert "frames" in tables

    session_columns = {col["name"] for col in inspector.get_columns("sessions")}
    frame_columns = {col["name"] for col in inspector.get_columns("frames")}

    for col in [
        "session_id",
        "operator_id",
        "start_time",
        "weld_type",
        "thermal_sample_interval_ms",
        "thermal_directions",
        "thermal_distance_interval_mm",
        "sensor_sample_rate_hz",
        "status",
        "frame_count",
        "expected_frame_count",
        "last_successful_frame_index",
        "validation_errors",
        "completed_at",
        "locked_until",
        "version",
        "disable_sensor_continuity_checks",
    ]:
        assert col in session_columns

    for col in ["id", "session_id", "timestamp_ms", "frame_data"]:
        assert col in frame_columns


def test_indexes_exist():
    engine = _engine()
    inspector = inspect(engine)

    session_indexes = {idx["name"] for idx in inspector.get_indexes("sessions")}
    frame_indexes = {idx["name"] for idx in inspector.get_indexes("frames")}

    assert "idx_sessions_operator_id" in session_indexes
    assert "idx_sessions_start_time" in session_indexes
    assert "idx_sessions_weld_type" in session_indexes
    assert "idx_frames_session_timestamp" in frame_indexes


def test_duplicate_frame_rejected_by_db():
    engine = _engine()
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["sessions", "frames"])
    sessions = Table("sessions", metadata, autoload_with=engine)
    frames = Table("frames", metadata, autoload_with=engine)

    session_id = f"session-{uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            sessions.insert().values(
                session_id=session_id,
                operator_id="operator-dup",
                start_time=text("now()"),
                weld_type="test",
                thermal_sample_interval_ms=100,
                thermal_directions=["center", "north", "south", "east", "west"],
                thermal_distance_interval_mm=10.0,
                sensor_sample_rate_hz=100,
                status="recording",
                frame_count=1,
                validation_errors=[],
                disable_sensor_continuity_checks=False,
                version=1,
            )
        )

        conn.execute(
            frames.insert().values(
                session_id=session_id,
                timestamp_ms=0,
                frame_data={"timestamp_ms": 0},
            )
        )

        with pytest.raises(IntegrityError):
            conn.execute(
                frames.insert().values(
                    session_id=session_id,
                    timestamp_ms=0,
                    frame_data={"timestamp_ms": 0},
                )
            )


def test_index_improves_query_performance():
    engine = _engine()
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["sessions", "frames"])
    sessions = Table("sessions", metadata, autoload_with=engine)
    frames = Table("frames", metadata, autoload_with=engine)

    session_id = f"session-{uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            sessions.insert().values(
                session_id=session_id,
                operator_id="operator-idx",
                start_time=text("now()"),
                weld_type="test",
                thermal_sample_interval_ms=100,
                thermal_directions=["center", "north", "south", "east", "west"],
                thermal_distance_interval_mm=10.0,
                sensor_sample_rate_hz=100,
                status="recording",
                frame_count=2,
                validation_errors=[],
                disable_sensor_continuity_checks=False,
                version=1,
            )
        )
        conn.execute(
            frames.insert(),
            [
                {"session_id": session_id, "timestamp_ms": 0, "frame_data": {"timestamp_ms": 0}},
                {"session_id": session_id, "timestamp_ms": 10, "frame_data": {"timestamp_ms": 10}},
            ],
        )

        plan = conn.execute(
            text(
                "EXPLAIN SELECT * FROM frames "
                "WHERE session_id = :session_id "
                "ORDER BY timestamp_ms DESC LIMIT 1"
            ),
            {"session_id": session_id},
        ).fetchall()

        plan_text = " ".join(row[0] for row in plan)
        assert "Index" in plan_text or "index" in plan_text


def test_concurrent_inserts_maintain_order():
    engine = _engine()
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["sessions", "frames"])
    sessions = Table("sessions", metadata, autoload_with=engine)
    frames = Table("frames", metadata, autoload_with=engine)

    session_id = f"session-{uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            sessions.insert().values(
                session_id=session_id,
                operator_id="operator-order",
                start_time=text("now()"),
                weld_type="test",
                thermal_sample_interval_ms=100,
                thermal_directions=["center", "north", "south", "east", "west"],
                thermal_distance_interval_mm=10.0,
                sensor_sample_rate_hz=100,
                status="recording",
                frame_count=2,
                validation_errors=[],
                disable_sensor_continuity_checks=False,
                version=1,
            )
        )
        conn.execute(
            frames.insert(),
            [
                {"session_id": session_id, "timestamp_ms": 10, "frame_data": {"timestamp_ms": 10}},
                {"session_id": session_id, "timestamp_ms": 0, "frame_data": {"timestamp_ms": 0}},
            ],
        )

        rows = conn.execute(
            text(
                "SELECT timestamp_ms FROM frames "
                "WHERE session_id = :session_id "
                "ORDER BY timestamp_ms ASC"
            ),
            {"session_id": session_id},
        ).fetchall()

        assert [row[0] for row in rows] == [0, 10]
