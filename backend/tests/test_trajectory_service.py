"""Tests for trajectory service."""
from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, patch

from services.trajectory_service import (
    get_welder_trajectory,
    _extract_metric_scores,
    _compute_projection,
    RULE_TO_METRIC,
)
from models.scoring import SessionScore, ScoreRule
from schemas.trajectory import TrajectoryPoint, WelderTrajectory


def test_rule_to_metric_keys_match_rule_based():
    """RULE_TO_METRIC keys must match rule_based.py rule_id strings."""
    expected = {
        "angle_consistency",
        "thermal_symmetry",
        "amps_stability",
        "volts_stability",
        "heat_diss_consistency",
    }
    assert set(RULE_TO_METRIC.keys()) == expected


@pytest.fixture
def _check_rule_based_deps():
    """Fail fast if rule_based deps missing; avoids silent skip.
    Expect pytest to be run from project root with backend on PYTHONPATH
    (e.g. cd backend && pytest, or pytest backend/tests).
    """
    try:
        from scoring.rule_based import score_session
        from features.extractor import extract_features
        from data.mock_sessions import generate_expert_session
    except ImportError as e:
        pytest.fail(
            f"rule_ids test requires scoring.rule_based, features.extractor, data.mock_sessions: {e}"
        )


def test_rule_ids_from_score_session_match_rule_to_metric(_check_rule_based_deps):
    """rule_ids from score_session must be covered by RULE_TO_METRIC."""
    from scoring.rule_based import score_session
    from features.extractor import extract_features
    from data.mock_sessions import generate_expert_session

    session = generate_expert_session(session_id="sess_test")
    features = extract_features(session)
    score = score_session(session, features, None)
    rule_ids = {r.rule_id for r in score.rules}
    unmatched = rule_ids - set(RULE_TO_METRIC.keys())
    assert not unmatched, f"rule_based returned rule_ids not in RULE_TO_METRIC: {unmatched}"


def test_extract_metric_scores_passed_100_failed_0():
    """ScoreRule passed=True -> value 100; passed=False -> value 0."""
    score = SessionScore(
        total=60,
        rules=[
            ScoreRule(
                rule_id="angle_consistency",
                threshold=5.0,
                passed=True,
                actual_value=3.0,
            ),
            ScoreRule(
                rule_id="thermal_symmetry",
                threshold=10.0,
                passed=False,
                actual_value=15.0,
            ),
        ],
    )
    metrics = _extract_metric_scores(score)
    assert len(metrics) == 2
    angle = next(m for m in metrics if m.metric.value == "angle_consistency")
    thermal = next(m for m in metrics if m.metric.value == "thermal_symmetry")
    assert angle.value == 100.0
    assert thermal.value == 0.0


def test_compute_projection_returns_none_for_single_point():
    """<2 points -> trend/projection None."""
    dt = datetime.now(timezone.utc)
    points = [
        TrajectoryPoint(
            session_id="s1",
            session_date=dt,
            score_total=70,
            metrics=[],
            session_index=1,
        )
    ]
    slope, proj = _compute_projection(points)
    assert slope is None
    assert proj is None


def test_compute_projection_returns_values_for_two_points():
    """2 points -> trend and projected computed."""
    dt = datetime.now(timezone.utc)
    points = [
        TrajectoryPoint(
            session_id="s1",
            session_date=dt,
            score_total=70,
            metrics=[],
            session_index=1,
        ),
        TrajectoryPoint(
            session_id="s2",
            session_date=dt,
            score_total=80,
            metrics=[],
            session_index=2,
        ),
    ]
    slope, proj = _compute_projection(points)
    assert slope is not None
    assert proj is not None
    assert slope == 10.0
    assert proj == 90.0


def test_compute_projection_ascending_scores_yield_positive_slope():
    """Ascending score_total must produce positive slope (avoids sign inversion)."""
    dt = datetime.now(timezone.utc)
    points = [
        TrajectoryPoint(
            session_id=f"s{i}",
            session_date=dt,
            score_total=70 + i * 2,
            metrics=[],
            session_index=i + 1,
        )
        for i in range(5)
    ]
    slope, _ = _compute_projection(points)
    assert slope is not None
    assert slope > 0, "Ascending scores must yield positive slope"


@patch("services.trajectory_service.get_session_score")
def test_nan_score_total_skips_session(mock_get_score):
    """get_session_score returning total=NaN must skip session, not propagate."""
    mock_get_score.return_value = MagicMock(total=float("nan"), rules=[])
    mock_session = MagicMock()
    mock_session.session_id = "sess_nan"
    mock_session.start_time = datetime.now(timezone.utc)
    mock_session.operator_id = "welder1"
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        mock_session
    ]
    result = get_welder_trajectory("welder1", mock_db)
    assert len(result.points) == 0
    assert result.skipped_sessions_count == 1


@patch("services.trajectory_service.get_session_score")
def test_null_start_time_skips_session(mock_get_score):
    """Session with start_time=None must skip, not pass None to TrajectoryPoint."""
    mock_get_score.return_value = MagicMock(total=75.0, rules=[])
    mock_session = MagicMock()
    mock_session.session_id = "sess_null"
    mock_session.start_time = None
    mock_session.operator_id = "welder1"
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        mock_session
    ]
    result = get_welder_trajectory("welder1", mock_db)
    assert len(result.points) == 0
    assert result.skipped_sessions_count == 1
