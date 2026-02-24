#!/usr/bin/env python3
"""
Seed demo sessions from WELDER_ARCHETYPES into the database.
Idempotent: skips ONLY when existing count equals full expected count.
Used by deploy.sh.

Run from backend/ or with PYTHONPATH including backend.

  python -m scripts.seed_demo_data           # Skip if count matches
  python -m scripts.seed_demo_data --force   # Always wipe and re-seed (use after mock generator changes)
"""

import argparse
import logging
import random
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Ensure backend is on path when run via: python scripts/seed_demo_data.py
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from data.mock_welders import WELDER_ARCHETYPES
from data.mock_sessions import generate_session_for_welder
from database.connection import SessionLocal
from database.models import SessionModel


def _seed_demo_site(db) -> bool:
    """
    Seed one demo site and team for multi-site UI testing.
    Returns True if site was created or already existed; False if schema not ready
    (caller must not assume site exists).

    Note: db.get_bind() may return Connection (e.g. PgBouncer) instead of Engine;
    inspect() behavior can differ — test against your pooler config if needed.
    """
    from sqlalchemy import inspect

    inspector = inspect(db.get_bind())
    tables_raw = inspector.get_table_names()
    # Normalize: PostgreSQL may return schema-qualified names (e.g. 'public.sites')
    # or Row-like objects
    def _table_name(t) -> str:
        s = str(t)
        return s.split(".")[-1] if "." in s else s

    tables = [_table_name(t) for t in tables_raw]
    if "sites" not in tables:
        logger.warning("sites table missing. Run alembic upgrade 005 first.")
        return False

    # Half-migration check: sessions.team_id must exist
    # Assumes default schema (public); multi-schema setups may need schema param
    cols_raw = inspector.get_columns("sessions")
    # Dialect-agnostic: support dict (c['name']) and Row-like (getattr(c, 'name'))
    cols = [
        getattr(c, "name", c.get("name") if hasattr(c, "get") else None)
        for c in cols_raw
    ]
    if "team_id" not in cols:
        logger.warning(
            "sessions.team_id missing (half-migration?). "
            "Run alembic downgrade 004 && upgrade 005."
        )
        return False

    from models.site import Site, Team

    if db.query(Site).filter_by(id="site_demo_001").first():
        return True
    site = Site(id="site_demo_001", name="Harbor Shipyard", location="Singapore")
    team = Team(
        id="team_demo_001",
        site_id="site_demo_001",
        name="Bay 3 Welding Team",
    )
    db.add(site)
    db.add(team)
    db.commit()
    return True


SEED_DRILLS = [
    # angle_consistency
    {"target_metric": "angle_consistency",
     "title": "30-45-60 Angle Progression",
     "description": "Practice at 30°, 45°, and 60° for 5 minutes each. Focus on wrist stability. Use a guide block to feel the target angle before removing it.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "angle_consistency",
     "title": "Slow-Motion Angle Hold",
     "description": "Weld at half normal travel speed. Prioritise holding the torch angle constant over travel speed. Record 3 sessions.",
     "sessions_required": 3, "success_threshold": 72.0},
    {"target_metric": "angle_consistency",
     "title": "Angle Awareness Drill",
     "description": "Before each weld, verbally state the target angle. After each weld, estimate the actual average angle and compare to readout.",
     "sessions_required": 2, "success_threshold": 70.0},
    # thermal_symmetry
    {"target_metric": "thermal_symmetry",
     "title": "Reduced Travel Speed",
     "description": "Drop travel speed by 20%. Slower travel distributes heat more evenly across the joint width. Monitor N-S symmetry gauge.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "thermal_symmetry",
     "title": "Centreline Focus",
     "description": "Place a chalk line on the workpiece and keep the torch tip within 2mm of it throughout the weld.",
     "sessions_required": 2, "success_threshold": 70.0},
    {"target_metric": "thermal_symmetry",
     "title": "Pre-heat Pattern Practice",
     "description": "Apply pre-heat in a symmetrical pattern before welding. Verify N-S and E-W temps are within 5°C before starting.",
     "sessions_required": 2, "success_threshold": 72.0},
    # amps_stability
    {"target_metric": "amps_stability",
     "title": "Steady Contact Distance",
     "description": "Maintain consistent contact tip to work distance. Use a feeler gauge (12mm) to calibrate starting position before each run.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "amps_stability",
     "title": "Voltage-Amps Coupling Check",
     "description": "Verify machine settings match material spec sheet before each session. Check for worn contact tips.",
     "sessions_required": 2, "success_threshold": 70.0},
    # volts_stability
    {"target_metric": "volts_stability",
     "title": "Arc Length Consistency",
     "description": "Focus on maintaining constant arc length by watching the weld pool width. Practice on scrap for 10 minutes first.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "volts_stability",
     "title": "Travel Speed Uniformity",
     "description": "Use a metronome (80 BPM) to set travel rhythm. Consistent speed prevents voltage spikes from sudden pauses.",
     "sessions_required": 2, "success_threshold": 70.0},
    # heat_diss_consistency
    {"target_metric": "heat_diss_consistency",
     "title": "Cool-Down Interval Protocol",
     "description": "Add 30-second intervals between passes. Monitor center temp; do not start next pass until below 200°C.",
     "sessions_required": 3, "success_threshold": 70.0},
    {"target_metric": "heat_diss_consistency",
     "title": "Backstepping Technique",
     "description": "Practice backstep welding pattern (weld right-to-left in segments). Reduces cumulative heat buildup.",
     "sessions_required": 3, "success_threshold": 72.0},
]


def _seed_drills(db) -> None:
    """Seed drills table if not already populated. Idempotent."""
    from models.coaching import Drill

    if db.query(Drill).count() >= len(SEED_DRILLS):
        return
    for d in SEED_DRILLS:
        db.add(Drill(**d))
    db.commit()


def _seed_cert_standards(db) -> None:
    """Seed cert_standards table if not already populated. Idempotent."""
    from models.certification import CertStandard

    STANDARDS = [
        {
            "id": "aws_d1_1",
            "name": "AWS D1.1 Structural Welding",
            "required_score": 80.0,
            "sessions_required": 3,
            "weld_type": None,
        },
        {
            "id": "iso_9606",
            "name": "ISO 9606 Welding Qualification",
            "required_score": 85.0,
            "sessions_required": 4,
            "weld_type": None,
        },
        {
            "id": "internal_basic",
            "name": "Internal Basic Certification",
            "required_score": 65.0,
            "sessions_required": 2,
            "weld_type": None,
        },
    ]
    for s in STANDARDS:
        if not db.query(CertStandard).filter_by(id=s["id"]).first():
            db.add(CertStandard(**s))
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed demo sessions from WELDER_ARCHETYPES. Use --force to always re-seed (e.g. after mock generator changes)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Always wipe and re-seed; skip idempotent early-exit. Use after changing mock_sessions.py.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        session_ids = []
        for arch in WELDER_ARCHETYPES:
            welder_id = arch["welder_id"]
            n = arch["sessions"]
            for i in range(1, n + 1):
                session_ids.append(f"sess_{welder_id}_{i:03d}")

        expected_count = len(session_ids)
        existing = 0 if args.force else db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).count()

        if args.force:
            logger.info("--force: wiping and re-seeding all sessions.")

        if existing == expected_count:
            # Spot-check: first derived ID and first archetype operator_id
            sample_sid = session_ids[0]
            expected_operator_id = WELDER_ARCHETYPES[0]["welder_id"]
            sess = db.query(SessionModel).filter(
                SessionModel.session_id == sample_sid
            ).first()
            if sess is None or sess.operator_id != expected_operator_id:
                logger.warning(
                    f"Spot-check failed: {sample_sid} operator_id={getattr(sess, 'operator_id', None)} "
                    f"expected {expected_operator_id}. Re-seeding."
                )
                # Fall through to re-seed
            else:
                _seed_drills(db)
                _seed_cert_standards(db)
                site_ok = _seed_demo_site(db)
                if not site_ok:
                    logger.error(
                        "_seed_demo_site skipped (schema not ready); site_demo_001 may be missing."
                    )
                    sys.exit(1)
                from models.site import Site

                site = db.query(Site).filter_by(id="site_demo_001").first()
                if site is None:
                    logger.error(
                        "site_demo_001 missing after seed. Schema check may have passed "
                        "but site was not created."
                    )
                    sys.exit(1)
                logger.info("Demo data already complete, skipping.")
                return 0

        if existing > 0 and existing < expected_count:
            logger.warning(f"{existing}/{expected_count} sessions exist. Re-seeding all.")
        for s in db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).all():
            db.delete(s)
        db.flush()

        random.seed(42)
        for arch in WELDER_ARCHETYPES:
            welder_id = arch["welder_id"]
            arc_type = arch["arc"]
            n = arch["sessions"]
            for i in range(1, n + 1):
                sid = f"sess_{welder_id}_{i:03d}"
                session = generate_session_for_welder(welder_id, arc_type, i - 1, sid)
                model = SessionModel.from_pydantic(session)
                db.add(model)

        db.commit()
        logger.info(f"Demo data seeded: {len(session_ids)} sessions")
        _seed_drills(db)
        _seed_cert_standards(db)
        site_ok = _seed_demo_site(db)
        if not site_ok:
            logger.error(
                "_seed_demo_site skipped (schema not ready); site_demo_001 may be missing."
            )
            sys.exit(1)

        from models.site import Site

        site = db.query(Site).filter_by(id="site_demo_001").first()
        if site is None:
            logger.error(
                "site_demo_001 missing after seed. Schema check may have passed "
                "but site was not created."
            )
            sys.exit(1)
        return 0
    except Exception as e:
        import traceback

        logger.exception("Seeding failed: %s", e)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
