"""
Trajectory service — per-welder longitudinal score history.
Queries sessions by operator_id; returns chronological TrajectoryPoints.
Limits to last 50 sessions to avoid N×get_session_score latency >500ms.
Uses order_by(start_time.nulls_last(), session_id) for deterministic ordering.
Sessions with NULL start_time are SKIPPED (never passed to TrajectoryPoint).
Status filter uses SessionStatus.COMPLETE.value to match DB enum.
Validates score.total is finite before creating TrajectoryPoint; skips session if NaN/Infinity.
"""
import logging
import math
import statistics
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from database.models import SessionModel
from models.shared_enums import WeldMetric
from models.session import SessionStatus
from schemas.trajectory import TrajectoryPoint, WelderTrajectory
from schemas.shared import MetricScore, make_metric_score
from services.scoring_service import get_session_score

logger = logging.getLogger(__name__)

RULE_TO_METRIC = {
    "angle_consistency": WeldMetric.ANGLE_CONSISTENCY,
    "thermal_symmetry": WeldMetric.THERMAL_SYMMETRY,
    "amps_stability": WeldMetric.AMPS_STABILITY,
    "volts_stability": WeldMetric.VOLTS_STABILITY,
    "heat_diss_consistency": WeldMetric.HEAT_DISS_CONSISTENCY,
}

MAX_TRAJECTORY_SESSIONS = 50


def get_welder_trajectory(welder_id: str, db: DBSession) -> WelderTrajectory:
    """
    Returns chronological score history for a welder.
    welder_id maps to operator_id in sessions table.
    Limited to last MAX_TRAJECTORY_SESSIONS sessions.
    Order: start_time asc (NULLs last), session_id asc (tiebreaker).
    Uses SessionStatus.COMPLETE.value to ensure DB enum alignment.
    Skips sessions where get_session_score raises or returns non-finite total.
    Skips sessions where start_time is None (never creates TrajectoryPoint with null datetime).
    """
    status_complete = SessionStatus.COMPLETE.value

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status == status_complete,
        )
        .order_by(
            SessionModel.start_time.asc().nulls_last(),
            SessionModel.session_id.asc(),
        )
        .limit(MAX_TRAJECTORY_SESSIONS)
        .all()
    )

    points: List[TrajectoryPoint] = []
    skipped = 0
    display_index = 0
    for session in sessions:
        # Guard: TrajectoryPoint requires datetime; skip if start_time is NULL
        if session.start_time is None:
            logger.warning(
                "Skipped session %s (start_time is NULL)",
                session.session_id,
            )
            skipped += 1
            continue

        try:
            score = get_session_score(session.session_id, db)
        except ValueError as e:
            logger.warning(
                "Skipped session %s (get_session_score failed): %s",
                session.session_id,
                str(e),
            )
            skipped += 1
            continue
        except Exception as e:
            logger.warning(
                "Skipped session %s (unexpected error): %s",
                session.session_id,
                str(e),
                exc_info=True,
            )
            skipped += 1
            continue

        # Guard: reject NaN/Infinity before TrajectoryPoint
        total = getattr(score, "total", None)
        if total is None or not math.isfinite(float(total)):
            logger.warning(
                "Skipped session %s (score.total not finite: %r)",
                session.session_id,
                total,
            )
            skipped += 1
            continue

        display_index += 1
        metrics = _extract_metric_scores(score)
        points.append(
            TrajectoryPoint(
                session_id=session.session_id,
                session_date=session.start_time,
                score_total=float(total),
                metrics=metrics,
                session_index=display_index,
            )
        )

    trend_slope, projected = _compute_projection(points)

    return WelderTrajectory(
        welder_id=welder_id,
        points=points,
        trend_slope=trend_slope,
        projected_next_score=projected,
        skipped_sessions_count=skipped if skipped > 0 else None,
    )


def _extract_metric_scores(score) -> List[MetricScore]:
    """Maps ScoreRule.rule_id to MetricScore. Uses passed ? 100 : 0 per exploration."""
    result = []
    for rule in score.rules:
        metric = RULE_TO_METRIC.get(rule.rule_id)
        if metric:
            val = 100.0 if rule.passed else 0.0
            result.append(make_metric_score(metric, val))
        else:
            logger.debug(
                "Trajectory: rule_id %r not in RULE_TO_METRIC, skipping",
                rule.rule_id,
            )
    return result


def _compute_projection(points: List[TrajectoryPoint]) -> Tuple[Optional[float], Optional[float]]:
    """Linear regression on last 5 score_total values. Returns (slope, projected_next)."""
    recent = [p.score_total for p in points[-5:]]
    if len(recent) < 2:
        return None, None

    n = len(recent)
    x = list(range(n))
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(recent)

    numerator = sum((x[i] - x_mean) * (recent[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, round(recent[-1], 2)

    slope = numerator / denominator
    projected = recent[-1] + slope
    projected = max(0.0, min(100.0, projected))
    return round(slope, 4), round(projected, 2)
