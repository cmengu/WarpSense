"""Tests for sites API routes."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from main import app


@patch("main.check_db_connectivity", return_value=True)
def test_sites_health(mock_check_db):
    """GET /api/sites/health returns ok and router."""
    with TestClient(app) as client:
        r = client.get("/api/sites/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("router") == "sites"
