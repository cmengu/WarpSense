"""
Tests for sessions API endpoints
Verifies 501 responses for unimplemented endpoints
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_list_sessions_returns_501():
    """Verify /api/sessions returns 501 Not Implemented"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions")
        assert response.status_code == 501
        assert "not implemented" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_session_returns_501():
    """Verify /api/sessions/{id} returns 501 Not Implemented"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions/test-session-id")
        assert response.status_code == 501
        assert "not implemented" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_session_features_returns_501():
    """Verify /api/sessions/{id}/features returns 501 Not Implemented"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions/test-session-id/features")
        assert response.status_code == 501
        assert "not implemented" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_session_score_returns_501():
    """Verify /api/sessions/{id}/score returns 501 Not Implemented"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions/test-session-id/score")
        assert response.status_code == 501
        assert "not implemented" in response.json()["detail"].lower()
