"""
Contract test: frame shape from Frame.model_dump() must match
dict(FrameModel.frame_data) such that extract_features receives identical structure.
DB round-trip test verifies PostgreSQL JSONB serialization does not change shape.

When DATABASE_URL is set: test MUST run and pass — no silent skip.
When DATABASE_URL unset and CI=true: pytest fails with clear message.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.frame import Frame
from models.thermal import ThermalSnapshot, TemperaturePoint
from features.warp_features import extract_features, extract_asymmetry


def _make_frame_with_thermal(timestamp_ms: int = 0) -> dict:
    snap = ThermalSnapshot(
        distance_mm=10.0,
        readings=[
            TemperaturePoint(direction="north", temp_celsius=100.0),
            TemperaturePoint(direction="south", temp_celsius=80.0),
            TemperaturePoint(direction="east", temp_celsius=90.0),
            TemperaturePoint(direction="west", temp_celsius=85.0),
            TemperaturePoint(direction="center", temp_celsius=120.0),
        ],
    )
    f = Frame(
        timestamp_ms=timestamp_ms,
        angle_degrees=45.0,
        amps=150.0,
        volts=22.0,
        thermal_snapshots=[snap],
    )
    return f.model_dump()


def test_frame_model_dump_has_thermal_structure():
    d = _make_frame_with_thermal()
    assert "thermal_snapshots" in d
    assert len(d["thermal_snapshots"]) >= 1
    readings = d["thermal_snapshots"][0].get("readings", [])
    assert any(r.get("direction") == "center" for r in readings)


def test_extract_features_same_for_model_dump_and_plain_dict():
    d = _make_frame_with_thermal()
    window = [{**d, "angle_degrees": 45, "amps": 150, "volts": 22}] * 50
    feat1 = extract_features(window)
    plain = dict(d)
    window2 = [{**plain, "angle_degrees": 45, "amps": 150, "volts": 22}] * 50
    feat2 = extract_features(window2)
    assert feat1 == feat2


def test_extract_asymmetry_direction_case_insensitive():
    """DB or mock may return direction='NORTH'; extract_asymmetry normalizes to lowercase."""
    f_upper = {
        "thermal_snapshots": [
            {
                "readings": [
                    {"direction": "NORTH", "temp_celsius": 100},
                    {"direction": "SOUTH", "temp_celsius": 80},
                    {"direction": "EAST", "temp_celsius": 90},
                    {"direction": "WEST", "temp_celsius": 85},
                ]
            }
        ]
    }
    f_lower = {
        "thermal_snapshots": [
            {
                "readings": [
                    {"direction": "north", "temp_celsius": 100},
                    {"direction": "south", "temp_celsius": 80},
                    {"direction": "east", "temp_celsius": 90},
                    {"direction": "west", "temp_celsius": 85},
                ]
            }
        ]
    }
    assert extract_asymmetry(f_upper) == 20.0
    assert extract_asymmetry(f_lower) == 20.0


def test_extract_features_handles_jsonb_int_temp():
    d = _make_frame_with_thermal()
    readings_int = [
        {"direction": r["direction"], "temp_celsius": int(r["temp_celsius"])}
        for r in d["thermal_snapshots"][0]["readings"]
    ]
    d_int = {**d, "thermal_snapshots": [{"readings": readings_int}]}
    window = [{**d_int, "angle_degrees": 45, "amps": 150, "volts": 22}] * 50
    feat = extract_features(window)
    assert feat["temp_current"] == 120.0
    assert isinstance(feat["temp_current"], float)


def test_db_frame_data_shape_matches_model_dump():
    """
    Round-trip: insert Frame via FrameModel, query, compare dict(frame_data) to model_dump.
    When DATABASE_URL is set: MUST run and pass. Skip only if DB unreachable (connection error).
    When DATABASE_URL unset and CI=true: FAIL with message (Phase 2 cannot be validated).
    """
    import pytest
    from datetime import datetime, timezone

    db_url = os.environ.get("DATABASE_URL")
    in_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")

    if not db_url:
        if in_ci:
            pytest.fail(
                "DATABASE_URL not set in CI. Set DATABASE_URL for contract validation before deploy."
            )
        pytest.skip("DATABASE_URL not set")

    try:
        from database.connection import SessionLocal
        from database.models import FrameModel, SessionModel
    except ImportError:
        if in_ci:
            pytest.fail("database module not available; fix imports for CI")
        pytest.skip("database module not available")

    frame = Frame(
        timestamp_ms=0,
        angle_degrees=45.0,
        amps=150.0,
        volts=22.0,
        thermal_snapshots=[
            ThermalSnapshot(
                distance_mm=10.0,
                readings=[
                    TemperaturePoint(direction="north", temp_celsius=100.0),
                    TemperaturePoint(direction="south", temp_celsius=80.0),
                    TemperaturePoint(direction="east", temp_celsius=90.0),
                    TemperaturePoint(direction="west", temp_celsius=85.0),
                    TemperaturePoint(direction="center", temp_celsius=120.0),
                ],
            )
        ],
    )
    expected = frame.model_dump()

    db = SessionLocal()
    try:
        session_id = "_warp_contract_test"
        for f in db.query(FrameModel).filter_by(session_id=session_id).all():
            db.delete(f)
        db.query(SessionModel).filter_by(session_id=session_id).delete()
        db.commit()
        db.add(
            SessionModel(
                session_id=session_id,
                operator_id="test",
                start_time=datetime.now(timezone.utc),
                weld_type="mig",
                thermal_sample_interval_ms=100,
                thermal_directions=["north", "south", "east", "west", "center"],
                thermal_distance_interval_mm=1.0,
                sensor_sample_rate_hz=100,
                frame_count=1,
                validation_errors=[],
                disable_sensor_continuity_checks=True,
            )
        )
        db.flush()
        fm = FrameModel.from_pydantic(frame)
        fm.session_id = session_id
        db.add(fm)
        db.commit()
        db.refresh(fm)

        actual = dict(fm.frame_data)
        assert set(actual.keys()) == set(expected.keys())
        for k in expected:
            assert k in actual
            ev, av = expected[k], actual[k]
            if k == "thermal_snapshots":
                assert len(actual[k]) == len(expected[k])
                if actual[k]:
                    assert "readings" in actual[k][0]
        # extract_features must work on DB shape
        window = [{**actual, "angle_degrees": 45, "amps": 150, "volts": 22}] * 50
        feat = extract_features(window)
        assert "thermal_asymmetry" in feat
        assert feat["thermal_asymmetry"] >= 0
        for f in db.query(FrameModel).filter_by(session_id=session_id).all():
            db.delete(f)
        db.query(SessionModel).filter_by(session_id=session_id).delete()
        db.commit()
    except Exception as e:
        err_str = str(e).lower()
        if "could not connect" in err_str or "connection refused" in err_str:
            if in_ci:
                pytest.fail(f"DB unreachable in CI: {e}")
            pytest.skip(f"DB unreachable: {e}")
        if (
            "does not exist" in err_str
            or "relation" in err_str
            or "column" in err_str
        ):
            pytest.fail(
                f"DB schema mismatch: {e}. Run 'alembic upgrade head' — schema may be out of date."
            )
        raise
    finally:
        db.close()
