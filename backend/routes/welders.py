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
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from routes.sessions import get_db
from schemas.benchmark import WelderBenchmarks
from schemas.certification import WelderCertificationSummary
from schemas.coaching import CoachingPlanResponse
from services.benchmark_service import get_welder_benchmarks
from services.cert_service import get_certification_status
from services.coaching_service import assign_coaching_plan, get_coaching_plan
from services.trajectory_service import get_welder_trajectory
from schemas.trajectory import WelderTrajectory

router = APIRouter(prefix="/api/welders", tags=["welders"])


@router.get("/health")
async def welders_health():
    """Stub health check — confirms router is registered."""
    return {"status": "ok", "router": "welders"}


@router.get("/{welder_id}/trajectory", response_model=WelderTrajectory)
def get_trajectory(welder_id: str, db: OrmSession = Depends(get_db)):
    """Returns chronological score history for a welder."""
    return get_welder_trajectory(welder_id, db)


@router.get("/{welder_id}/benchmarks", response_model=WelderBenchmarks)
def get_benchmarks(welder_id: str, db: OrmSession = Depends(get_db)):
    """Returns per-metric benchmark for welder vs all other welders."""
    return get_welder_benchmarks(welder_id, db)


@router.get("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def get_coaching(welder_id: str, db: OrmSession = Depends(get_db)):
    """Returns active and completed coaching assignments for the welder."""
    return get_coaching_plan(welder_id, db)


@router.post("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def trigger_coaching_assignment(welder_id: str, db: OrmSession = Depends(get_db)):
    """Auto-assign drills based on welder benchmarks."""
    benchmark_data = get_welder_benchmarks(welder_id, db)
    return assign_coaching_plan(welder_id, benchmark_data, db)


@router.get(
    "/{welder_id}/certification-status",
    response_model=WelderCertificationSummary,
)
def get_certifications(welder_id: str, db: OrmSession = Depends(get_db)):
    """Returns certification readiness for welder across all standards."""
    return get_certification_status(welder_id, db)
