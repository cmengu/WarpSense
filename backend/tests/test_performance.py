"""
Step 20: Performance benchmark tests.
Uses pytest-benchmark when available. Run: pip install pytest-benchmark

How to adjust thresholds based on hardware:
1. Run benchmarks to get baseline: pytest tests/test_performance.py -v --benchmark-only
2. Inspect output: each test reports mean, median, stddev (seconds)
3. Set thresholds: BASELINE * 1.5 or 2.0 (safety margin for CI/slower machines)
4. Override via env: PERFORMANCE_VALIDATE_S=2, PERFORMANCE_COMPARE_S=5, etc.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import pytest

# Configurable thresholds (seconds). Override via env for your hardware.
PERFORMANCE_VALIDATE_S = float(os.environ.get("PERFORMANCE_VALIDATE_S", "2.0"))
PERFORMANCE_COMPARE_S = float(os.environ.get("PERFORMANCE_COMPARE_S", "5.0"))
PERFORMANCE_SERIALIZE_S = float(os.environ.get("PERFORMANCE_SERIALIZE_S", "3.0"))

try:
    import pytest_benchmark
    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False

if HAS_BENCHMARK:
    from datetime import datetime, timezone
    from models.frame import Frame
    from models.session import Session, SessionStatus
    from models.thermal import TemperaturePoint, ThermalSnapshot
    from services.comparison_service import compare_sessions
    from data.mock_sessions import generate_expert_session, generate_novice_session

if not HAS_BENCHMARK:
    def test_performance_requires_pytest_benchmark():
        pytest.skip(
            "pytest-benchmark required for performance tests. "
            "Run: pip install pytest-benchmark"
        )
else:
    def _readings(temp=400.0):
        return [
            TemperaturePoint(direction="center", temp_celsius=temp),
            TemperaturePoint(direction="north", temp_celsius=temp - 10),
            TemperaturePoint(direction="south", temp_celsius=temp - 20),
            TemperaturePoint(direction="east", temp_celsius=temp - 15),
            TemperaturePoint(direction="west", temp_celsius=temp - 25),
        ]

    def test_validate_30k_frame_session_under_threshold(benchmark):
        """Validate 30k frame session completes within PERFORMANCE_VALIDATE_S."""
        from data.mock_sessions import generate_large_session
        large = generate_large_session()
        dumped = large.model_dump(mode="json")
        result = benchmark(lambda: Session.model_validate(dumped))
        assert result is not None
        assert result.frame_count == 30000
        assert benchmark.stats["mean"] < PERFORMANCE_VALIDATE_S, (
            f"Validation took {benchmark.stats['mean']:.2f}s, threshold={PERFORMANCE_VALIDATE_S}s"
        )

    def test_compare_two_sessions_under_threshold(benchmark):
        """Compare two 1500-frame sessions within PERFORMANCE_COMPARE_S."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        deltas = benchmark(compare_sessions, expert, novice)
        assert len(deltas) > 0
        assert benchmark.stats["mean"] < PERFORMANCE_COMPARE_S, (
            f"Comparison took {benchmark.stats['mean']:.2f}s, threshold={PERFORMANCE_COMPARE_S}s"
        )

    def test_serialize_session_to_json_under_threshold(benchmark):
        """Serialize 1500-frame session to JSON within PERFORMANCE_SERIALIZE_S."""
        session = generate_expert_session()
        result = benchmark(lambda: session.model_dump_json())
        assert len(result) > 1000
        assert benchmark.stats["mean"] < PERFORMANCE_SERIALIZE_S, (
            f"Serialize took {benchmark.stats['mean']:.2f}s, threshold={PERFORMANCE_SERIALIZE_S}s"
        )

    def test_deserialize_session_from_json_under_threshold(benchmark):
        """Deserialize 1500-frame session from JSON within PERFORMANCE_SERIALIZE_S."""
        session = generate_expert_session()
        json_str = session.model_dump_json()
        result = benchmark(lambda: Session.model_validate_json(json_str))
        assert result.frame_count == session.frame_count
        assert benchmark.stats["mean"] < PERFORMANCE_SERIALIZE_S, (
            f"Deserialize took {benchmark.stats['mean']:.2f}s, threshold={PERFORMANCE_SERIALIZE_S}s"
        )
