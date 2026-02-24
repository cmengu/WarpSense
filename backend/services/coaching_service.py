"""
Coaching service — drill assignment and progress evaluation.

DEPENDENCY RULE:
  coaching_service → benchmark_service (one-way only, lazy import in fn body)
  benchmark_service must NEVER import coaching_service.

Constants:
  AUTO_ASSIGN_THRESHOLD = 60.0
  MAX_ACTIVE_ASSIGNMENTS = 2
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from models.coaching import CoachingAssignment, Drill
from models.shared_enums import CoachingStatus
from schemas.benchmark import WelderBenchmarks
from schemas.coaching import (
    CoachingAssignmentResponse,
    CoachingPlanResponse,
    DrillResponse,
)

logger = logging.getLogger(__name__)
AUTO_ASSIGN_THRESHOLD = 60.0
MAX_ACTIVE_ASSIGNMENTS = 2


def get_coaching_plan(welder_id: str, db: DBSession) -> CoachingPlanResponse:
    """Fetch active and recently completed coaching assignments for a welder."""
    from services.benchmark_service import get_welder_benchmarks

    active = (
        db.query(CoachingAssignment)
        .filter(
            CoachingAssignment.welder_id == welder_id,
            CoachingAssignment.status == "active",
        )
        .all()
    )
    completed = (
        db.query(CoachingAssignment)
        .filter(
            CoachingAssignment.welder_id == welder_id,
            CoachingAssignment.status == "complete",
        )
        .order_by(CoachingAssignment.completed_at.desc())
        .limit(10)
        .all()
    )

    benchmarks = get_welder_benchmarks(welder_id, db)
    metric_values = {m.metric.value: m.welder_value for m in benchmarks.metrics}

    def enrich(assignment: CoachingAssignment) -> CoachingAssignmentResponse:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        if not drill:
            raise ValueError(f"Drill id={assignment.drill_id} not found")
        current_metric_value = metric_values.get(drill.target_metric)
        return CoachingAssignmentResponse(
            id=assignment.id,
            welder_id=assignment.welder_id,
            drill=DrillResponse.model_validate(drill),
            assigned_at=assignment.assigned_at,
            status=CoachingStatus(assignment.status),
            sessions_completed=assignment.sessions_completed,
            completed_at=assignment.completed_at,
            current_metric_value=current_metric_value,
        )

    return CoachingPlanResponse(
        welder_id=welder_id,
        active_assignments=[enrich(a) for a in active],
        completed_assignments=[enrich(a) for a in completed],
        auto_assigned=False,
    )


def assign_coaching_plan(
    welder_id: str,
    benchmark_data: WelderBenchmarks,
    db: DBSession,
) -> CoachingPlanResponse:
    """
    Auto-assign drills for metrics where welder is below AUTO_ASSIGN_THRESHOLD.
    Skips metrics already covered by active assignments. Max MAX_ACTIVE_ASSIGNMENTS.
    """
    active = (
        db.query(CoachingAssignment)
        .filter(
            CoachingAssignment.welder_id == welder_id,
            CoachingAssignment.status == "active",
        )
        .all()
    )
    if len(active) >= MAX_ACTIVE_ASSIGNMENTS:
        plan = get_coaching_plan(welder_id, db)
        plan.auto_assigned = False
        return plan

    covered_metrics = set()
    for a in active:
        drill = db.query(Drill).filter_by(id=a.drill_id).first()
        if drill:
            covered_metrics.add(drill.target_metric)

    worst_metrics = sorted(
        [
            m
            for m in benchmark_data.metrics
            if m.metric.value not in covered_metrics
        ],
        key=lambda m: m.percentile,
    )

    new_assignments = 0
    for bm in worst_metrics:
        if new_assignments + len(active) >= MAX_ACTIVE_ASSIGNMENTS:
            break
        if bm.percentile >= 50:
            continue
        drill = (
            db.query(Drill)
            .filter_by(target_metric=bm.metric.value)
            .order_by(Drill.success_threshold.asc())
            .first()
        )
        if not drill:
            continue
        db.add(
            CoachingAssignment(
                welder_id=welder_id,
                drill_id=drill.id,
                status="active",
                sessions_completed=0,
            )
        )
        new_assignments += 1

    if new_assignments > 0:
        db.commit()

    plan = get_coaching_plan(welder_id, db)
    plan.auto_assigned = new_assignments > 0
    return plan


def evaluate_progress(welder_id: str, db: DBSession) -> int:
    """
    Increment sessions_completed for active assignments and mark complete
    when welder's current metric value meets success_threshold.

    Lazy import of benchmark_service to prevent circular dependency at module load.
    Called from sessions score handler after persisting score_total.

    Returns:
        Number of assignments newly marked complete.
    """
    from services.benchmark_service import get_welder_benchmarks

    active = (
        db.query(CoachingAssignment)
        .filter(
            CoachingAssignment.welder_id == welder_id,
            CoachingAssignment.status == "active",
        )
        .all()
    )
    if not active:
        return 0

    benchmarks = get_welder_benchmarks(welder_id, db)
    metric_values = {
        m.metric.value: m.welder_value for m in benchmarks.metrics
    }
    completed = 0

    for assignment in active:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        if not drill:
            continue
        assignment.sessions_completed += 1
        current_val = metric_values.get(drill.target_metric, 0.0)
        if current_val >= drill.success_threshold:
            assignment.status = "complete"
            assignment.completed_at = datetime.now(timezone.utc)
            completed += 1

    db.commit()
    return completed
