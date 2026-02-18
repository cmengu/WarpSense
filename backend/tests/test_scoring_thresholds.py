"""
Tests for scoring with different thresholds (TIG vs MIG).
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models import SessionModel, WeldThresholdModel
from data.mock_sessions import generate_expert_session
from features.extractor import extract_features
from scoring.rule_based import score_session
from services.threshold_service import get_thresholds


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seeded_weld_thresholds(db_session):
    for weld_type, a, aw, ac, tw, tc, amps, volts, hd in [
        ("mig", 45.0, 5.0, 15.0, 60.0, 80.0, 5.0, 1.0, 40.0),
        ("tig", 75.0, 10.0, 20.0, 60.0, 80.0, 5.0, 1.0, 40.0),
    ]:
        db_session.add(
            WeldThresholdModel(
                weld_type=weld_type,
                angle_target_degrees=a,
                angle_warning_margin=aw,
                angle_critical_margin=ac,
                thermal_symmetry_warning_celsius=tw,
                thermal_symmetry_critical_celsius=tc,
                amps_stability_warning=amps,
                volts_stability_warning=volts,
                heat_diss_consistency=hd,
            )
        )
    db_session.commit()


def test_score_uses_tig_thresholds(db_session, seeded_weld_thresholds):
    """TIG session uses TIG thresholds (angle_target 75, angle_warning 10)."""
    session = generate_expert_session(session_id="sess_tig_001")
    session = session.model_copy(update={"process_type": "tig"})
    thresholds = get_thresholds(db_session, "tig")
    features = extract_features(
        session, angle_target_deg=thresholds.angle_target_degrees
    )
    score = score_session(session, features, thresholds)
    # angle_consistency rule should use threshold 10 (TIG)
    angle_rule = next(r for r in score.rules if r.rule_id == "angle_consistency")
    assert angle_rule.threshold == 10


def test_score_uses_mig_thresholds(db_session, seeded_weld_thresholds):
    """MIG session uses MIG thresholds (angle_target 45, angle_warning 5)."""
    session = generate_expert_session(session_id="sess_mig_001")
    session = session.model_copy(update={"process_type": "mig"})
    thresholds = get_thresholds(db_session, "mig")
    features = extract_features(
        session, angle_target_deg=thresholds.angle_target_degrees
    )
    score = score_session(session, features, thresholds)
    angle_rule = next(r for r in score.rules if r.rule_id == "angle_consistency")
    assert angle_rule.threshold == 5
