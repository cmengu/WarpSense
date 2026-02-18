"""
Verifies warp-risk route registration — catches unapplied merge.
Source-based: no main import (avoids DATABASE_URL at import).
Backend integration test uses API_BASE env (default localhost:8000).
"""
from pathlib import Path


def test_warp_risk_route_registered():
    """Asserts merge was applied: predictions_router imported and included."""
    import pytest

    main_path = Path(__file__).resolve().parent.parent / "main.py"
    if not main_path.exists():
        pytest.skip("main.py not in expected location")
    source = main_path.read_text()
    assert "predictions_router" in source
    assert "include_router(predictions_router)" in source


def test_warp_risk_endpoint_reachable():
    """
    Integration: with backend running and seed done, GET warp-risk returns 200.
    Skips if requests unavailable or backend not reachable.
    Uses API_BASE env (backend tests) — default http://localhost:8000.

    CI GATE: When CI runs the backend (e.g. services: backend in GHA), this test MUST pass — do NOT skip.
    When CI does NOT run backend: test skips; deploy requires documented manual verification:
      curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sessions/sess_novice_001/warp-risk
    Must return 200 before deploy. See CI Gate section.
    """
    import os
    import pytest

    SESSION_ID = os.environ.get("SESSION_ID", "sess_novice_001")
    try:
        import requests
    except ImportError:
        pytest.skip("requests not installed")

    base = os.environ.get("API_BASE", "http://localhost:8000")
    url = f"{base}/api/sessions/{SESSION_ID}/warp-risk"
    try:
        r = requests.get(url, timeout=5)
    except Exception:
        pytest.skip("Backend not reachable")
    assert r.status_code == 200, f"warp-risk returned {r.status_code}"
    data = r.json()
    assert "session_id" in data
    assert "model_available" in data
    assert data["risk_level"] in ("ok", "warning", "critical")
