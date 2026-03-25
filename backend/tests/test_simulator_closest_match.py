"""
Regression tests for GET /api/simulator/closest-match (simulator corpus match plan).

Uses a freshly trained WeldClassifier on generate_feature_dataset() so DEFECTIVE
is present without relying on weld_classifier.joblib or a running server.
"""

import pytest

from features.session_feature_extractor import generate_feature_dataset
from features.weld_classifier import WeldClassifier
from routes.simulator import simulator_closest_match
import services.warp_service as warp_service


@pytest.fixture
def trained_classifier():
    clf = WeldClassifier()
    clf.train(generate_feature_dataset())
    return clf


def test_closest_match_bad_weld_defective_corpus(trained_classifier, monkeypatch):
    monkeypatch.setattr(warp_service, "_al_feature_cache", {})
    warp_service._build_al_feature_cache()
    monkeypatch.setattr(
        "routes.simulator.get_classifier", lambda: trained_classifier
    )

    r = simulator_closest_match(
        heat_input_level=2200.0,
        torch_angle_deviation=22.0,
        arc_stability=0.48,
    )
    assert "al_defective" in r.session_id
    assert r.quality_class == "DEFECTIVE"
    assert r.rework_cost_usd == 4200
    assert r.distance >= 0.0


def test_closest_match_good_weld_hot_or_nominal(trained_classifier, monkeypatch):
    monkeypatch.setattr(warp_service, "_al_feature_cache", {})
    warp_service._build_al_feature_cache()
    monkeypatch.setattr(
        "routes.simulator.get_classifier", lambda: trained_classifier
    )

    r = simulator_closest_match(
        heat_input_level=6500.0,
        torch_angle_deviation=2.0,
        arc_stability=0.93,
    )
    assert "al_hot_clean" in r.session_id or "al_nominal" in r.session_id
    assert r.quality_class == "GOOD"
    assert r.rework_cost_usd == 0
