"""
Shared pytest fixtures for backend tests.
Bypasses DB connectivity check when tests use in-memory SQLite.
Bypasses WarpSense init so tests don't require GROQ_API_KEY.
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


@pytest.fixture(autouse=True)
def _patch_warp_init_for_testclient(monkeypatch):
    """
    Bypass WarpSense init so lifespan and lazy init don't require GROQ_API_KEY.
    Patches both main (lifespan) and services.warp_service (get_graph/get_classifier).
    """
    def _noop_init():
        pass

    try:
        import main as main_module
        monkeypatch.setattr(main_module, "init_warp_components", _noop_init)
    except ImportError:
        pass
    try:
        import services.warp_service as ws
        monkeypatch.setattr(ws, "init_warp_components", _noop_init)
    except ImportError:
        pass
