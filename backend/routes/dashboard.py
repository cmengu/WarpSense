"""
Dashboard API routes
Exposes endpoints for dashboard data
"""

from fastapi import APIRouter
from models import DashboardData
from data.mock_data import mock_dashboard_data

router = APIRouter()


@router.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    """
    Returns dashboard data from mock_data.py

    This endpoint reads from backend/data/mock_data.py and returns
    the data as a validated DashboardData Pydantic model.

    To update the data, edit backend/data/mock_data.py and refresh
    the frontend.
    """
    # Convert Python dict to Pydantic model for validation
    # This ensures the data structure matches DashboardData exactly
    return DashboardData(**mock_dashboard_data)
