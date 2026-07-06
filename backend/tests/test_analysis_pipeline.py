"""
Unit tests for warpsense.analysis.analyze() — the pure pipeline seam.

The pipeline stages (extractor, classifier, graph) are mocked; these tests
pin the seam's contract, not the stages' behavior.
"""

from unittest.mock import MagicMock, patch

import pytest

from warpsense.analysis import AnalysisResult, analyze


def _run(progress_cb=None, extract_side_effect=None):
    classifier = MagicMock()
    graph = MagicMock()
    frames = [{"timestamp_ms": 0}]
    with patch("warpsense.analysis.pipeline.SessionFeatureExtractor") as ext_cls:
        extractor = ext_cls.return_value
        if extract_side_effect is not None:
            extractor.extract.side_effect = extract_side_effect
        result = analyze(
            "sess_x", frames, classifier=classifier, graph=graph, progress_cb=progress_cb
        )
    return result, extractor, classifier, graph


def test_analyze_returns_all_three_stages():
    result, extractor, classifier, graph = _run()
    assert isinstance(result, AnalysisResult)
    assert result.features is extractor.extract.return_value
    assert result.prediction is classifier.predict.return_value
    assert result.report is graph.assess.return_value
    extractor.extract.assert_called_once_with("sess_x", [{"timestamp_ms": 0}])
    classifier.predict.assert_called_once_with(result.features)


def test_analyze_without_progress_cb_uses_assess():
    _, _, _, graph = _run()
    graph.assess.assert_called_once()
    graph.assess_with_progress.assert_not_called()


def test_analyze_with_progress_cb_uses_assess_with_progress():
    cb = MagicMock()
    result, _, classifier, graph = _run(progress_cb=cb)
    graph.assess.assert_not_called()
    graph.assess_with_progress.assert_called_once_with(
        classifier.predict.return_value, result.features, cb
    )
    assert result.report is graph.assess_with_progress.return_value


def test_analyze_propagates_extractor_rejection():
    with pytest.raises(ValueError, match="too few arc-on frames"):
        _run(extract_side_effect=ValueError("too few arc-on frames"))
