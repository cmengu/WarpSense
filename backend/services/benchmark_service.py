"""
Benchmark service — computes per-metric percentile rankings.
Population: all welders' MOST RECENT complete session with a score.

IMPORT RULE: This file must NEVER import coaching_service.
Other services may import this one, never the reverse.
"""
import logging
import statistics
from sqlalchemy.orm import Session as DBSession

from database.models import SessionModel
from models.session import SessionStatus
from models.shared_enums import WeldMetric
from schemas.benchmark import MetricBenchmark, WelderBenchmarks
from schemas.shared import METRIC_LABELS
from services.scoring_service import get_session_score
from services.trajectory_service import _extract_metric_scores

logger = logging.getLogger(__name__)
TOP_PERCENTILE = 75.0
BOTTOM_PERCENTILE = 25.0


def get_welder_benchmarks(welder_id: str, db: DBSession) -> WelderBenchmarks:
    """
    Compute per-metric percentile rankings for welder vs all other welders.
    Population: each welder's most recent COMPLETE session with a valid score.
    """
    status_complete = SessionStatus.COMPLETE.value
    operator_ids = [
        row.operator_id
        for row in db.query(SessionModel.operator_id)
        .filter(
            SessionModel.status == status_complete,
            SessionModel.operator_id.isnot(None),
        )
        .distinct()
        .all()
    ]

    population: dict[str, dict[WeldMetric, float]] = {}
    for op_id in operator_ids:
        latest = (
            db.query(SessionModel)
            .filter(
                SessionModel.operator_id == op_id,
                SessionModel.status == status_complete,
            )
            .order_by(SessionModel.start_time.desc())
            .first()
        )
        if not latest:
            continue
        try:
            score = get_session_score(latest.session_id, db)
        except (ValueError, Exception) as e:
            logger.debug("Skipped session %s for benchmark: %s", latest.session_id, e)
            continue
        metric_scores = _extract_metric_scores(score)
        population[op_id] = {ms.metric: ms.value for ms in metric_scores}

    if welder_id not in population:
        logger.warning("Welder %s not in benchmark population", welder_id)
        return WelderBenchmarks(
            welder_id=welder_id,
            population_size=0,
            metrics=[],
            overall_percentile=0.0,
        )

    welder_metrics = population[welder_id]
    metrics_result = []

    for metric in WeldMetric:
        values = [v[metric] for v in population.values() if metric in v]
        if len(values) < 2:
            continue
        welder_val = welder_metrics.get(metric, 0.0)
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        pop_min = min(values)
        pop_max = max(values)
        percentile = _compute_percentile(welder_val, values)
        if percentile >= TOP_PERCENTILE:
            tier = "top"
        elif percentile <= BOTTOM_PERCENTILE:
            tier = "bottom"
        else:
            tier = "mid"
        metrics_result.append(
            MetricBenchmark(
                metric=metric,
                label=METRIC_LABELS[metric],
                welder_value=round(welder_val, 2),
                population_mean=round(mean, 2),
                population_min=round(pop_min, 2),
                population_max=round(pop_max, 2),
                population_std=round(std, 2),
                percentile=round(percentile, 1),
                tier=tier,
            )
        )

    welder_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status == status_complete,
        )
        .order_by(SessionModel.start_time.desc())
        .first()
    )
    # Use index access for single-column query; SQLAlchemy Row may not expose score_total attr.
    rows = (
        db.query(SessionModel.score_total)
        .filter(
            SessionModel.status == status_complete,
            SessionModel.score_total.isnot(None),
        )
        .all()
    )
    all_scores = [float(r[0]) for r in rows if r[0] is not None]
    overall_pct = 0.0
    if welder_session and welder_session.score_total is not None and all_scores:
        overall_pct = _compute_percentile(
            float(welder_session.score_total), [float(x) for x in all_scores]
        )

    return WelderBenchmarks(
        welder_id=welder_id,
        population_size=len(population),
        metrics=metrics_result,
        overall_percentile=round(overall_pct, 1),
    )


def _compute_percentile(value: float, population: list[float]) -> float:
    """Percentile = (count below value / total) * 100."""
    below = sum(1 for v in population if v < value)
    return (below / len(population)) * 100
