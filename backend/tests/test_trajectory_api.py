"""Tests for trajectory API route."""
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from main import app
from schemas.trajectory import WelderTrajectory, TrajectoryPoint


@patch("main.check_db_connectivity", return_value=True)
@patch("routes.welders.get_welder_trajectory")
def test_trajectory_returns_welder_trajectory_shape(mock_get_trajectory, mock_check_db):
    """GET /api/welders/{id}/trajectory returns welder_id, points, trend_slope, projected_next_score."""
    mock_get_trajectory.return_value = WelderTrajectory(
        welder_id="mike-chen",
        points=[
            TrajectoryPoint(
                session_id="sess_1",
                session_date=datetime.now(timezone.utc),
                score_total=68.0,
                metrics=[],
                session_index=1,
            ),
        ],
        trend_slope=None,
        projected_next_score=None,
    )
    with TestClient(app) as client:
        r = client.get("/api/welders/mike-chen/trajectory")
    assert r.status_code == 200
    data = r.json()
    assert data["welder_id"] == "mike-chen"
    assert "points" in data
    assert isinstance(data["points"], list)
    assert "trend_slope" in data
    assert "projected_next_score" in data


@patch("main.check_db_connectivity", return_value=True)
@patch("routes.welders.get_welder_trajectory")
def test_trajectory_empty_welder_returns_empty_points(mock_get_trajectory, mock_check_db):
    """Welder with no complete sessions returns points:[], null trend/projection."""
    mock_get_trajectory.return_value = WelderTrajectory(
        welder_id="nonexistent",
        points=[],
        trend_slope=None,
        projected_next_score=None,
    )
    with TestClient(app) as client:
        r = client.get("/api/welders/nonexistent-welder-xyz/trajectory")
    assert r.status_code == 200
    data = r.json()
    assert data["points"] == []
    assert data.get("trend_slope") is None
    assert data.get("projected_next_score") is None


@pytest.mark.integration
@patch("main.check_db_connectivity", return_value=True)
def test_trajectory_integration_with_seeded_db(mock_check_db):
    """Integration: hit real trajectory service. Requires DB. Run with: pytest -m integration"""
    with TestClient(app) as client:
        r = client.get("/api/welders/mike-chen/trajectory")
    assert r.status_code == 200
    data = r.json()
    assert "welder_id" in data
    assert "points" in data
    assert isinstance(data["points"], list)
