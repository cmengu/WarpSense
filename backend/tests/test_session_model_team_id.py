"""Regression: SessionModel team_id does not break from_pydantic/to_pydantic."""
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from datetime import datetime, timezone

from database.models import SessionModel
from models.session import Session


def test_from_pydantic_sets_team_id_none():
    s = Session(
        session_id="x",
        operator_id="o",
        start_time=datetime.now(timezone.utc),
        weld_type="t",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frame_count=0,
        frames=[],
    )
    m = SessionModel.from_pydantic(s)
    assert m.team_id is None


def test_to_pydantic_omits_team_id():
    s = Session(
        session_id="x",
        operator_id="o",
        start_time=datetime.now(timezone.utc),
        weld_type="t",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frame_count=0,
        frames=[],
    )
    m = SessionModel.from_pydantic(s)
    p = m.to_pydantic()
    assert not hasattr(p, "team_id") or getattr(p, "team_id", None) is None
