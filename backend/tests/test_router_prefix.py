"""
Tests for router prefix correctness
Verifies no double /api/api/ prefix and routes are registered correctly
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


def test_no_double_api_prefix():
    """Verify no routes contain /api/api/"""
    routes = [route.path for route in app.routes]
    double_api_routes = [r for r in routes if "/api/api/" in r]
    assert len(double_api_routes) == 0, f"Found double /api/api/ prefix in routes: {double_api_routes}"


def test_sessions_routes_exist():
    """Verify sessions routes are registered at correct paths"""
    routes = [route.path for route in app.routes]
    # Check for /api/sessions route
    assert any("/api/sessions" in r and r.count("/api/sessions") == 1 for r in routes), \
        f"Sessions route not found. Available routes: {routes}"
    # Check for /api/sessions/{session_id} route
    assert any("/api/sessions/" in r for r in routes), \
        f"Sessions detail route not found. Available routes: {routes}"


def test_welders_routes_exist():
    """Verify welders router is registered — catches omitted include_router(welders_router)."""
    routes = [route.path for route in app.routes]
    assert any("/api/welders" in r for r in routes), (
        f"Welders routes not found. Add app.include_router(welders_router). Available routes: {routes}"
    )
