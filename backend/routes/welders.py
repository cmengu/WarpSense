"""
Welder-scoped API routes.
All /api/welders/{welder_id}/... endpoints live here.
Do NOT add welder routes to sessions.py or aggregate.py.

When routes need DB: from routes.sessions import get_db

Routes added per batch:
  Batch 2: GET /api/welders/{welder_id}/trajectory
  Batch 3: GET /api/welders/{welder_id}/benchmarks
  Batch 3: GET /api/welders/{welder_id}/coaching-plan
  Batch 3: POST /api/welders/{welder_id}/coaching-plan
  Batch 3: GET /api/welders/{welder_id}/certification-status
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/welders", tags=["welders"])


@router.get("/health")
async def welders_health():
    """Stub health check — confirms router is registered."""
    return {"status": "ok", "router": "welders"}
