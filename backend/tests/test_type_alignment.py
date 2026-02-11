"""
Tests for type alignment between Python Pydantic models and TypeScript types.
Verifies structure matches to prevent drift. WeldingSession removed; uses canonical Session.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.scoring import ScoreRule, SessionScore
from models.session import Session, SessionStatus


def test_score_rule_structure():
    """Verify ScoreRule has correct fields matching TypeScript (snake_case)."""
    rule = ScoreRule(rule_id="test", threshold=0.0, passed=False)
    assert hasattr(rule, "rule_id")
    assert hasattr(rule, "threshold")
    assert hasattr(rule, "passed")
    assert isinstance(rule.rule_id, str)
    assert isinstance(rule.threshold, float)
    assert isinstance(rule.passed, bool)


def test_session_score_structure():
    """Verify SessionScore has correct fields matching TypeScript SessionScore."""
    score = SessionScore(total=0, rules=[])
    assert hasattr(score, "total")
    assert hasattr(score, "rules")
    assert isinstance(score.total, int)
    assert isinstance(score.rules, list)


def test_session_structure_snake_case():
    """Verify Session uses snake_case fields matching frontend types."""
    session = Session(
        session_id="test",
        operator_id="op-1",
        start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=[],
        frame_count=0,
        status=SessionStatus.RECORDING,
    )
    assert hasattr(session, "session_id")
    assert hasattr(session, "operator_id")
    assert hasattr(session, "start_time")
    assert hasattr(session, "thermal_sample_interval_ms")
    assert hasattr(session, "frame_count")
    assert session.session_id == "test"
