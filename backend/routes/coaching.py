"""
Coaching plan API routes.
GET /api/welders/{welder_id}/coaching-plan — fetch plan
POST /api/welders/{welder_id}/coaching-plan — trigger assignment
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from routes.sessions import get_db
from schemas.coaching import CoachingPlanResponse
from services.benchmark_service import get_welder_benchmarks
from services.coaching_service import assign_coaching_plan, get_coaching_plan

router = APIRouter(prefix="/api/welders", tags=["welders"])


@router.get("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def get_coaching_plan_route(
    welder_id: str, db: OrmSession = Depends(get_db)
) -> CoachingPlanResponse:
    """Returns active and completed coaching assignments for the welder."""
    return get_coaching_plan(welder_id, db)


@router.post("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def post_coaching_plan_assign(
    welder_id: str, db: OrmSession = Depends(get_db)
) -> CoachingPlanResponse:
    """
    Auto-assign drills based on welder benchmarks.
    Uses benchmark service to find weak metrics and assign drills.
    """
    benchmarks = get_welder_benchmarks(welder_id, db)
    return assign_coaching_plan(welder_id, benchmarks, db)
