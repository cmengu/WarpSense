"""Tests for welders API routes."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from main import app
from schemas.benchmark import MetricBenchmark, WelderBenchmarks


@patch("main.check_db_connectivity", return_value=True)
def test_welders_health(mock_check_db):
    """GET /api/welders/health returns ok and router."""
    with TestClient(app) as client:
        r = client.get("/api/welders/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("router") == "welders"


@patch("main.check_db_connectivity", return_value=True)
@patch("routes.welders.get_welder_benchmarks")
def test_benchmarks_returns_welder_benchmarks_shape(mock_get_benchmarks, mock_check_db):
    """GET /api/welders/{id}/benchmarks returns welder_id, population_size, metrics, overall_percentile."""
    mock_get_benchmarks.return_value = WelderBenchmarks(
        welder_id="mike-chen",
        population_size=3,
        metrics=[
            MetricBenchmark(
                metric="angle_consistency",
                label="Angle Consistency",
                welder_value=72.0,
                population_mean=65.0,
                population_min=40.0,
                population_max=90.0,
                population_std=15.0,
                percentile=75.0,
                tier="top",
            ),
        ],
        overall_percentile=68.5,
    )
    with TestClient(app) as client:
        r = client.get("/api/welders/mike-chen/benchmarks")
    assert r.status_code == 200
    data = r.json()
    assert data["welder_id"] == "mike-chen"
    assert data["population_size"] == 3
    assert "metrics" in data
    assert isinstance(data["metrics"], list)
    assert data["overall_percentile"] == 68.5
