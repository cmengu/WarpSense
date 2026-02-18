#!/usr/bin/env python3
"""
Prototype: validate that mock_sessions arc generation produces target score ranges.
Must use mock_sessions.generate_session_for_welder — same path as seed/Phase 2.

IMPORTANT: Run with a fresh Python process (not after calling seed in same process).
If using mock_sessions/seed in same run, call random.seed(42) immediately before
each PASS_BAND check inside the loop to avoid random state drift.

Tuning guide (when scores fail):
  - fast_learner scores low → tighten _arc_angle_tight stddev (reduce looseness).
  - declining scores high → increase _arc_angle_drift drift_factor.

Run from project root: PYTHONPATH=backend python backend/scripts/prototype_arc_scoring.py
"""

import random
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))

from data.mock_sessions import generate_session_for_welder
from database.connection import SessionLocal
from features.extractor import extract_features
from scoring.rule_based import score_session
from services.threshold_service import get_thresholds

# Explicit pass bands: arc -> (session_idx, min_score, max_score)
# base ± 15 for session 0; target ± 15 for session 4
PASS_BANDS = [
    ("fast_learner", 0, 43, 73),
    ("fast_learner", 4, 59, 98),
    ("declining", 0, 61, 91),
    ("declining", 4, 40, 70),
    ("volatile", 0, 38, 92),
    ("volatile", 2, 38, 92),
    ("consistent_expert", 0, 73, 103),
    ("consistent_expert", 4, 78, 108),
]


def main():
    print("Prototype: mock_sessions.generate_session_for_welder → Features → Score")
    print("=" * 60)
    thresholds = None
    try:
        db = SessionLocal()
        try:
            pt = "mig"  # All mock sessions use default process_type
            thresholds = get_thresholds(db, pt)
        finally:
            db.close()
    except Exception as e:
        print(f"Note: Could not load thresholds from DB ({e}), using module constants")

    failures = []
    for arc, s_idx, min_s, max_s in PASS_BANDS:
        # Fresh seed before each check — avoids drift if run after seed in same process
        random.seed(42)
        sid = f"sess_{arc}_{s_idx + 1:03d}"
        session = generate_session_for_welder(f"proto-{arc}", arc, s_idx, sid)
        angle_target = (
            thresholds.angle_target_degrees if thresholds else 45.0
        )
        features = extract_features(session, angle_target_deg=angle_target)
        sc = score_session(session, features, thresholds)
        ok = min_s <= sc.total <= max_s
        status = "OK" if ok else "FAIL"
        print(f"{arc} session {s_idx}: score={sc.total:.1f} [{min_s}-{max_s}] {status}")
        if not ok:
            failures.append((arc, s_idx, sc.total, min_s, max_s))

    if failures:
        print("\nFAILED: Scores outside pass bands:")
        for arc, s_idx, score, min_s, max_s in failures:
            print(f"  {arc} s{s_idx}: {score} not in [{min_s},{max_s}]")
        sys.exit(1)
    print("\nDone. All arcs in range.")


if __name__ == "__main__":
    main()
