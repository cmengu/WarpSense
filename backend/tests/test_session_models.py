"""
Tests for Pydantic session models (canonical Session type).
WeldingSession removed; uses Session with Frame[] from canonical time-series contract.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.session import Session, SessionStatus
from models.scoring import ScoreRule, SessionScore
from models.thermal import TemperaturePoint, ThermalSnapshot


def _readings(temp=400.0):
    return [
        TemperaturePoint(direction="center", temp_celsius=temp),
        TemperaturePoint(direction="north", temp_celsius=temp - 10),
        TemperaturePoint(direction="south", temp_celsius=temp - 20),
        TemperaturePoint(direction="east", temp_celsius=temp - 15),
        TemperaturePoint(direction="west", temp_celsius=temp - 25),
    ]


def test_score_rule_serialization():
    """Test ScoreRule model serialization."""
    rule = ScoreRule(rule_id="pressure", threshold=25.0, passed=True)
    assert rule.rule_id == "pressure"
    assert rule.threshold == 25.0
    assert rule.passed is True


def test_session_score_serialization():
    """Test SessionScore model serialization."""
    rules = [
        ScoreRule(rule_id="pressure", threshold=25.0, passed=True),
        ScoreRule(rule_id="temperature", threshold=1200.0, passed=True),
    ]
    score = SessionScore(total=20, rules=rules)
    assert score.total == 20
    assert len(score.rules) == 2
    assert score.rules[0].rule_id == "pressure"


def test_session_serialization_round_trip():
    """Test Session model serialization/deserialization round-trip."""
    frames = [
        Frame(
            timestamp_ms=0,
            volts=22.0,
            amps=150.0,
            angle_degrees=45.0,
            thermal_snapshots=[
                ThermalSnapshot(distance_mm=10.0, readings=_readings(400.0)),
            ],
        ),
        Frame(timestamp_ms=10, volts=22.1, amps=150.1, angle_degrees=45.1, thermal_snapshots=[]),
    ]
    session = Session(
        session_id="test-123",
        operator_id="op-1",
        start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=frames,
        frame_count=2,
        status=SessionStatus.RECORDING,
        disable_sensor_continuity_checks=True,
    )
    assert session.session_id == "test-123"
    assert session.frame_count == 2
    assert len(session.frames) == 2

    dumped = session.model_dump(mode="json")
    restored = Session.model_validate(dumped)
    assert restored.session_id == session.session_id
    assert restored.frame_count == session.frame_count
