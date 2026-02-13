"""
Shared pytest fixtures for backend tests.
Bypasses DB connectivity check when tests use in-memory SQLite.
"""

import pytest


@pytest.fixture(autouse=True)
def _patch_db_connectivity_for_testclient(monkeypatch):
    """
    Bypass startup DB check when TestClient is used.
    Tests that use in-memory SQLite override get_db and don't need PostgreSQL.
    """
    try:
        import main as main_module
        monkeypatch.setattr(main_module, "check_db_connectivity", lambda: True)
    except ImportError:
        pass  # main not importable (e.g. missing deps) — other skip handles it
