"""
WWAD aggregate service.
Computes team-level KPIs from session metadata + score_total (no frame loading).
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from database.models import SessionModel


def get_aggregate_kpis(
    db: OrmSession,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    include_sessions: bool = False,
) -> dict:
    """
    Aggregate sessions by date range. COMPLETE only.
    Returns kpis, trend, calendar; optionally sessions for export.

    Uses metadata + score_total only; never loads frames.
    """
    q = db.query(SessionModel).filter(SessionModel.status == "complete")

    if date_start:
        q = q.filter(SessionModel.start_time >= date_start)
    if date_end:
        de = (
            datetime.fromisoformat(date_end).date()
            if isinstance(date_end, str)
            else date_end
        )
        end_exclusive = datetime.combine(
            de + timedelta(days=1), datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        q = q.filter(SessionModel.start_time < end_exclusive)

    q = q.order_by(SessionModel.start_time.asc())
    sessions = q.all()

    # KPIs — never divide by zero; avg_score only when scored list non-empty
    scored = [s for s in sessions if s.score_total is not None]
    if len(scored) == 0:
        avg_score = None
    else:
        total_score = sum(s.score_total for s in scored)
        avg_score = total_score / len(scored)

    session_count = len(sessions)

    by_operator = defaultdict(list)
    for s in scored:
        by_operator[s.operator_id].append(s.score_total)

    top_performer = None
    if by_operator:
        best_avg = max(sum(v) / len(v) for v in by_operator.values())
        candidates = [
            op
            for op, scores in by_operator.items()
            if sum(scores) / len(scores) == best_avg
        ]
        top_performer = min(candidates) if candidates else None

    rework_count = sum(1 for s in scored if s.score_total < 60)

    # Trend: avg score by date (YYYY-MM-DD)
    by_date_score = defaultdict(list)
    for s in scored:
        dt = s.start_time.date() if hasattr(s.start_time, "date") else s.start_time
        key = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)[:10]
        by_date_score[key].append(s.score_total)
    trend = [
        {"date": d, "value": sum(v) / len(v)}
        for d, v in sorted(by_date_score.items())
    ]

    # Calendar: sessions per day
    by_date_count = defaultdict(int)
    for s in sessions:
        dt = s.start_time.date() if hasattr(s.start_time, "date") else s.start_time
        key = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)[:10]
        by_date_count[key] += 1
    calendar = [{"date": d, "value": c} for d, c in sorted(by_date_count.items())]

    result = {
        "kpis": {
            "avg_score": round(avg_score, 1) if avg_score is not None else None,
            "session_count": session_count,
            "top_performer": top_performer,
            "rework_count": rework_count,
        },
        "trend": trend,
        "calendar": calendar,
        "sessions_truncated": False,
    }

    if include_sessions:
        sessions_list = sessions[:1000]
        result["sessions"] = [
            {
                "session_id": s.session_id,
                "operator_id": s.operator_id,
                "weld_type": s.weld_type,
                "start_time": s.start_time.isoformat() if s.start_time else "",
                "score_total": s.score_total,
                "frame_count": s.frame_count,
            }
            for s in sessions_list
        ]
        result["sessions_truncated"] = len(sessions) > 1000

    return result
