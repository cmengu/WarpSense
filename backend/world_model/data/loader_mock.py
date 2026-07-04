"""
Mock loader — DEV/PLUMBING ONLY (D4). Any number computed on mock data is a
pipeline check, never a result.

Wraps the three generators in backend/data/mock_sessions.py and converts their
Frame lists through the shared frames_to_session_tensor path. The generators are
deterministic per session_index (isolated random.Random seeds), so a corpus is
reproducible from (kind, index) alone.
"""

from data.mock_sessions import (
    _AL_PARAM_CONFIG,
    _generate_aluminium_parametric_frames,
    _generate_continuous_novice_frames,
    _generate_stitch_expert_frames,
)
from world_model.data.schema import SessionTensor, frames_to_session_tensor

PARAMETRIC_ARC_TYPES = sorted(_AL_PARAM_CONFIG.keys())

# Coarse quality class per parametric arc type — matches the corpus intent in
# mock_sessions.py (heat/angle/arc-on-ratio degradation order). Used only for
# plumbing checks of class-conditional code paths.
_ARC_TYPE_QUALITY = {
    "al_hot_clean": "GOOD",
    "al_nominal": "GOOD",
    "al_cold": "MARGINAL",
    "al_angled": "MARGINAL",
    "al_defective": "DEFECTIVE",
}


def load_mock_session(kind: str, session_index: int, num_frames: int = 1500) -> SessionTensor:
    """kind ∈ {'stitch_expert', 'continuous_novice'} ∪ PARAMETRIC_ARC_TYPES."""
    if kind == "stitch_expert":
        frames = _generate_stitch_expert_frames(session_index, num_frames)
        quality = "GOOD"
    elif kind == "continuous_novice":
        frames = _generate_continuous_novice_frames(session_index, num_frames)
        quality = "MARGINAL"
    elif kind in _AL_PARAM_CONFIG:
        frames = _generate_aluminium_parametric_frames(kind, session_index, num_frames)
        quality = _ARC_TYPE_QUALITY[kind]
    else:
        raise ValueError(f"unknown mock kind {kind!r}")
    return frames_to_session_tensor(
        frames,
        session_id=f"mock_{kind}_{session_index:04d}",
        source="mock",
        extra_meta={"kind": kind, "quality_class": quality},
    )


def load_mock_corpus(n_sessions: int, num_frames: int = 1500) -> list[SessionTensor]:
    """Round-robin over all generator kinds → n_sessions deterministic sessions."""
    kinds = ["stitch_expert", "continuous_novice", *PARAMETRIC_ARC_TYPES]
    return [
        load_mock_session(kinds[i % len(kinds)], session_index=i, num_frames=num_frames)
        for i in range(n_sessions)
    ]
