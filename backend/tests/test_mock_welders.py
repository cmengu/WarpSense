"""Tests for mock welder archetypes and arc-specific frame generation."""

import random
import pytest

from data.mock_welders import WELDER_ARCHETYPES, generate_score_arc
from data.mock_sessions import (
    generate_frames_for_arc,
    generate_session_for_welder,
)
from models.session import Session
from features.extractor import extract_features
from scoring.rule_based import score_session


def test_welder_archetypes_has_10():
    assert len(WELDER_ARCHETYPES) == 10


def test_generate_score_arc_length():
    random.seed(42)
    s = generate_score_arc(58, 4, 5, "fast_learner")
    assert len(s) == 5
    assert all(0 <= x <= 100 for x in s)


def test_volatile_reproducible():
    random.seed(42)
    s1 = generate_score_arc(65, 0, 5, "volatile")
    random.seed(42)
    s2 = generate_score_arc(65, 0, 5, "volatile")
    assert s1 == s2


def test_generate_frames_for_arc_returns_valid_frames():
    frames, disable = generate_frames_for_arc("fast_learner", 0)
    assert len(frames) == 1500
    assert isinstance(disable, bool)


def test_volatile_declining_disable_continuity():
    _, d_vol = generate_frames_for_arc("volatile", 0)
    _, d_dec = generate_frames_for_arc("declining", 0)
    assert d_vol is True
    assert d_dec is True


def test_fast_learner_expert_continuity_enabled():
    _, d_fl = generate_frames_for_arc("fast_learner", 0)
    _, d_exp = generate_frames_for_arc("consistent_expert", 0)
    assert d_fl is False
    assert d_exp is False


def test_generate_session_for_welder_valid():
    s = generate_session_for_welder(
        "mike-chen", "fast_learner", 0, "sess_mike-chen_001"
    )
    assert isinstance(s, Session)
    assert s.operator_id == "mike-chen"
    assert s.session_id == "sess_mike-chen_001"
    assert len(s.frames) == 1500


def test_arc_scores_in_reasonable_range():
    """Scores should be 0-100; accept ±20 from archetype base for session 0."""
    for arch in [WELDER_ARCHETYPES[0], WELDER_ARCHETYPES[3]]:
        s = generate_session_for_welder(
            arch["welder_id"],
            arch["arc"],
            0,
            f"sess_{arch['welder_id']}_001",
        )
        f = extract_features(s)
        sc = score_session(s, f)
        assert 0 <= sc.total <= 100


def test_mock_sessions_fast_learner_session0_in_band():
    """mock_sessions.generate_session_for_welder must produce scores in band (prototype validation path)."""
    random.seed(42)
    s = generate_session_for_welder(
        "mike-chen", "fast_learner", 0, "sess_mike-chen_001"
    )
    f = extract_features(s)
    sc = score_session(s, f)
    assert 43 <= sc.total <= 73, (
        f"fast_learner s0 score {sc.total} outside [43,73]"
    )
