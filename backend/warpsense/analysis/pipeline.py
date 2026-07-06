"""
The weld-analysis pipeline: extract features -> classify -> assess.

Pure orchestration. Callers own I/O on both sides: loading frames
(db/frames.get_session_frames_raw) and persisting the report
(services/warp_service). This function is synchronous and may block on
network I/O inside graph.assess (Groq) — async callers must run it in an
executor, never on the event loop.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from warpsense.agents.warpsense_agent import WeldQualityReport
from warpsense.agents.warpsense_graph import WarpSenseGraph
from warpsense.classifier.weld_classifier import WeldClassifier, WeldPrediction
from warpsense.features.session_feature_extractor import (
    SessionFeatureExtractor,
    SessionFeatures,
)


@dataclass
class AnalysisResult:
    """Everything the pipeline produced, so callers can persist or inspect any stage."""

    features: SessionFeatures
    prediction: WeldPrediction
    report: WeldQualityReport


def analyze(
    session_id: str,
    frames: list[dict],
    *,
    classifier: WeldClassifier,
    graph: WarpSenseGraph,
    progress_cb: Optional[Callable[[dict], None]] = None,
) -> AnalysisResult:
    """
    Run the full pipeline for one session.

    frames: raw frame dicts, ascending by timestamp_ms, shaped like
    Frame.model_dump() (the contract of db/frames.get_session_frames_raw).

    progress_cb: when given, the graph runs assess_with_progress and fires
    per-stage events on whatever thread this function runs in — forwarding
    to an event loop is the caller's job (loop.call_soon_threadsafe).

    Raises ValueError when the extractor rejects the session
    (e.g. < 100 arc-on frames after volts/amps filtering).
    """
    extractor = SessionFeatureExtractor()
    features = extractor.extract(session_id, frames)

    prediction = classifier.predict(features)

    if progress_cb is None:
        report = graph.assess(prediction, features)
    else:
        report = graph.assess_with_progress(prediction, features, progress_cb)

    return AnalysisResult(features=features, prediction=prediction, report=report)
