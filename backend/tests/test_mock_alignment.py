"""
Step 11 verification test: Mock alignment check.

Formula: overlap_pct = len(expert_times & novice_times) / len(expert_times) * 100

Verification result (when PASS):
  - overlap_at_least_90_percent: overlap_pct >= 90
  - overlap_100_percent: overlap_pct == 100 (both use range(0, 15000, 10))
  - shared_count_equals_expert_count: len(shared) == len(expert_timestamps)
  - same_frame_count: len(expert.frames) == len(novice.frames) == 1500

Pass Criteria: ≥90% overlap before Step 12 (Compare page).
If FAIL: Fix mock_sessions.py — ensure both use same duration_ms and frame_interval_ms.
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from data.mock_sessions import generate_expert_session, generate_novice_session


def _compute_alignment(expert, novice):
    """Compute shared timestamp overlap. Returns (shared_count, expert_count, overlap_pct)."""
    expert_times = {f.timestamp_ms for f in expert.frames}
    novice_times = {f.timestamp_ms for f in novice.frames}
    shared = expert_times & novice_times
    expert_count = len(expert_times)
    overlap_pct = (len(shared) / expert_count * 100) if expert_count > 0 else 0
    return len(shared), expert_count, overlap_pct


class TestMockAlignmentStep11:
    """Step 11 verification: expert and novice sessions have aligned timestamps."""

    def test_overlap_at_least_90_percent(self) -> None:
        """Shared timestamps / expert timestamps >= 90%."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        shared_count, expert_count, overlap_pct = _compute_alignment(expert, novice)
        assert overlap_pct >= 90, (
            f"Timestamp overlap must be >= 90%, got {overlap_pct:.1f}% "
            f"(shared={shared_count}, expert={expert_count})"
        )

    def test_overlap_100_percent(self) -> None:
        """Both use same range(0, 15000, 10) → expect 100% overlap."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        shared_count, expert_count, overlap_pct = _compute_alignment(expert, novice)
        assert overlap_pct == 100, (
            f"Mock sessions should have 100% overlap (same duration_ms, frame_interval_ms), "
            f"got {overlap_pct:.1f}%"
        )

    def test_shared_count_equals_expert_count(self) -> None:
        """Every expert timestamp has a matching novice frame."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        shared_count, expert_count, _ = _compute_alignment(expert, novice)
        assert shared_count == expert_count, (
            f"All {expert_count} expert timestamps should have novice match, "
            f"got {shared_count} shared"
        )

    def test_same_frame_count(self) -> None:
        """Expert and novice have same frame count (duration_ms and frame_interval identical)."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        assert len(expert.frames) == len(novice.frames), (
            f"Expert has {len(expert.frames)} frames, novice has {len(novice.frames)} — "
            "ensure same duration_ms and frame_interval_ms in generate_frames"
        )
