"""
Mock dashboard data - SINGLE SOURCE OF TRUTH
Edit this file to update dashboard data. Changes will automatically reflect
in the frontend when it fetches from the API.

To update dashboard data:
1. Edit the dictionaries below
2. Save the file (backend will auto-reload if using uvicorn --reload)
3. Refresh the frontend browser
4. Frontend will fetch updated data from GET /api/dashboard
"""

# Mock dashboard data matching the DashboardData structure
mock_dashboard_data = {
    "metrics": [
        {
            "id": "1",
            "title": "Total Users",
            "value": 12543,
            "change": 12.5,
            "trend": "up",
        },
        {
            "id": "2",
            "title": "Revenue",
            "value": "$45,231",
            "change": -2.3,
            "trend": "down",
        },
        {
            "id": "3",
            "title": "Active Sessions",
            "value": 892,
            "change": 5.2,
            "trend": "up",
        },
        {"id": "4", "title": "Conversion Rate", "value": "3.2%", "trend": "neutral"},
    ],
    "charts": [
        {
            "id": "1",
            "type": "line",
            "title": "User Growth",
            "color": "#3b82f6",
            "data": [
                {"date": "2024-01", "value": 1000},
                {"date": "2024-02", "value": 1200},
                {"date": "2024-03", "value": 1500},
                {"date": "2024-04", "value": 1800},
                {"date": "2024-05", "value": 2100},
                {"date": "2024-06", "value": 2400},
            ],
        },
        {
            "id": "2",
            "type": "bar",
            "title": "Revenue by Category",
            "color": "#10b981",
            "data": [
                {"category": "Product A", "value": 12000},
                {"category": "Product B", "value": 19000},
                {"category": "Product C", "value": 8000},
                {"category": "Product D", "value": 15000},
            ],
        },
        {
            "id": "3",
            "type": "pie",
            "title": "User Distribution",
            "data": [
                {"name": "Desktop", "value": 45},
                {"name": "Mobile", "value": 35},
                {"name": "Tablet", "value": 20},
            ],
        },
    ],
}
