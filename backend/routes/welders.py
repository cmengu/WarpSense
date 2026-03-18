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

from database.models import WeldQualityReportModel
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


def _clamp_quality_trend_days(days: int) -> int:
    """Clamp days to [1, 90]. Negative or zero -> 1; >90 -> 90."""
    return max(1, min(days, 90))


@router.get("/{welder_id}/quality-trend")
def get_quality_trend(
    welder_id: str,
    days: int = 30,
    db: OrmSession = Depends(get_db),
):
    """
    Returns 30-day rolling quality disposition trend for a welder.
    welder_id maps to operator_id in the sessions and weld_quality_reports tables.

    Query param:
      days: lookback window in days (default 30, max 90)

    Returns:
      welder_id, days, cutoff_timestamp, total_sessions_analysed,
      disposition_counts (PASS/CONDITIONAL/REWORK_REQUIRED), reports list.
    """
    from datetime import datetime, timedelta, timezone

    days = _clamp_quality_trend_days(days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    reports = (
        db.query(WeldQualityReportModel)
        .filter(
            WeldQualityReportModel.operator_id == welder_id,
            WeldQualityReportModel.report_timestamp >= cutoff,
        )
        .order_by(WeldQualityReportModel.report_timestamp.desc())
        .all()
    )

    disposition_counts = {"PASS": 0, "CONDITIONAL": 0, "REWORK_REQUIRED": 0}
    for r in reports:
        if r.disposition in disposition_counts:
            disposition_counts[r.disposition] += 1

    return {
        "welder_id": welder_id,
        "days": days,
        "cutoff_timestamp": cutoff.isoformat(),
        "total_sessions_analysed": len(reports),
        "disposition_counts": disposition_counts,
        "reports": [
            {
                "session_id": r.session_id,
                "disposition": r.disposition,
                "quality_class": r.quality_class,
                "confidence": r.confidence,
                "report_timestamp": r.report_timestamp.isoformat(),
            }
            for r in reports
        ],
    }
