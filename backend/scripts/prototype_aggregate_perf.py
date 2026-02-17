#!/usr/bin/env python3
"""
Prototype: Measure aggregate & batch scoring performance for WWAD exploration.

Run from backend/ with: python scripts/prototype_aggregate_perf.py
Requires: PostgreSQL seeded with sess_expert_001, sess_novice_001 (dev seed).

Critical path: Can we aggregate 500+ sessions with scores in < 3s?
"""

import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database.connection import SessionLocal
from database.models import SessionModel, FrameModel
from features.extractor import extract_features
from scoring.rule_based import score_session


def query_sessions_metadata_only(db, date_start=None, date_end=None):
    """Query session metadata (no frames). Returns list of (session_id, operator_id, weld_type, start_time, frame_count)."""
    q = db.query(
        SessionModel.session_id,
        SessionModel.operator_id,
        SessionModel.weld_type,
        SessionModel.start_time,
        SessionModel.frame_count,
    )
    if date_start:
        q = q.filter(SessionModel.start_time >= date_start)
    if date_end:
        q = q.filter(SessionModel.start_time <= date_end)
    return q.all()


def batch_score_sessions(db, session_ids, limit=None):
    """
    Load sessions with frames, extract features, score. Returns [(session_id, score_total)].
    """
    ids = session_ids[:limit] if limit else session_ids
    results = []
    for sid in ids:
        session_model = (
            db.query(SessionModel)
            .options(joinedload(SessionModel.frames))
            .filter_by(session_id=sid)
            .first()
        )
        if not session_model:
            continue
        session = session_model.to_pydantic()
        features = extract_features(session)
        score = score_session(session, features)
        results.append((sid, score.total))
    return results


def aggregate_counts(db, date_start=None, date_end=None):
    """Aggregate: session_count, by operator_id, by weld_type (no frames loaded)."""
    q = db.query(SessionModel)
    if date_start:
        q = q.filter(SessionModel.start_time >= date_start)
    if date_end:
        q = q.filter(SessionModel.start_time <= date_end)
    sessions = q.all()
    count = len(sessions)
    by_operator = {}
    by_weld_type = {}
    for s in sessions:
        by_operator[s.operator_id] = by_operator.get(s.operator_id, 0) + 1
        by_weld_type[s.weld_type] = by_weld_type.get(s.weld_type, 0) + 1
    return {"count": count, "by_operator": by_operator, "by_weld_type": by_weld_type}


def main():
    db = SessionLocal()
    try:
        print("=== WWAD Aggregate Performance Prototype ===\n")

        # 1. Metadata-only query (no frames)
        t0 = time.perf_counter()
        meta = query_sessions_metadata_only(db)
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"1. Metadata-only query ({len(meta)} sessions): {elapsed:.1f} ms")

        # 2. Aggregate counts (no frames)
        t0 = time.perf_counter()
        agg = aggregate_counts(db)
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"2. Aggregate counts (count, by_operator, by_weld_type): {elapsed:.1f} ms")
        print(f"   -> count={agg['count']}, operators={list(agg['by_operator'].keys())}")

        # 3. Batch score N sessions (loads frames)
        session_ids = [m.session_id for m in meta]
        for n in [2, 5] if len(session_ids) >= 5 else [min(2, len(session_ids))]:
            if n > len(session_ids):
                continue
            t0 = time.perf_counter()
            scored = batch_score_sessions(db, session_ids, limit=n)
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"3. Batch score {n} sessions (with frames): {elapsed:.1f} ms -> {scored}")

        # Extrapolation
        if len(session_ids) >= 2:
            t0 = time.perf_counter()
            scored = batch_score_sessions(db, session_ids, limit=min(10, len(session_ids)))
            elapsed = (time.perf_counter() - t0) * 1000
            per_session = elapsed / len(scored) if scored else 0
            print(f"\n4. Extrapolation: {per_session:.0f} ms/session")
            print(f"   500 sessions ≈ {500 * per_session / 1000:.1f} s (target: < 3s)")
            if 500 * per_session / 1000 > 3:
                print("   -> RECOMMENDATION: Persist score_total column; compute on session complete")

        print("\n=== Prototype complete ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
