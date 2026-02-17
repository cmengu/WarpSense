"""
WWAD aggregate API route.
GET /api/sessions/aggregate returns KPIs, trend, calendar for supervisor dashboard.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.aggregate import AggregateKPIResponse
from routes.sessions import get_db
from services.aggregate_service import get_aggregate_kpis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions/aggregate", response_model=AggregateKPIResponse)
async def get_sessions_aggregate(
    date_start: Optional[str] = Query(
        None, description="Start date YYYY-MM-DD (UTC); inclusive"
    ),
    date_end: Optional[str] = Query(
        None, description="End date YYYY-MM-DD (UTC); inclusive"
    ),
    include_sessions: bool = Query(
        False, description="Include session list for export"
    ),
    db=Depends(get_db),
):
    """
    Aggregate session KPIs for supervisor dashboard.
    COMPLETE sessions only. Uses metadata + score_total; no frame loading.

    Timezone: All dates are interpreted as UTC. date_end is inclusive.
    """
    start = time.perf_counter()
    now = datetime.now(timezone.utc)
    if not date_end:
        date_end = now.date().isoformat()
    if not date_start:
        date_start = (now - timedelta(days=7)).date().isoformat()

    try:
        ds = datetime.fromisoformat(date_start).date()
        de = datetime.fromisoformat(date_end).date()
    except ValueError:
        raise HTTPException(400, "Invalid date format; use YYYY-MM-DD")
    if ds > de:
        raise HTTPException(400, "date_start must be <= date_end")

    if (de - ds).days > 90:
        raise HTTPException(400, "Date range must be <= 90 days")

    data = get_aggregate_kpis(
        db,
        date_start=ds.isoformat(),
        date_end=de.isoformat(),
        include_sessions=include_sessions,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "aggregate",
        extra={
            "date_start": ds.isoformat(),
            "date_end": de.isoformat(),
            "duration_ms": elapsed_ms,
            "sessions_truncated": data.get("sessions_truncated", False),
        },
    )
    return AggregateKPIResponse(**data)
