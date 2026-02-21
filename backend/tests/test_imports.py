"""Import order tests — detect circular dependencies early.
Run first in CI (e.g. pytest tests/test_imports.py tests/...) to fail fast."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_no_circular_import():
    """Import routes.sessions, schemas.shared, models in sequence without circular import."""
    import routes.sessions  # noqa: F401
    import schemas.shared  # noqa: F401
    from models import WeldMetric  # noqa: F401
    from schemas.shared import MetricScore, make_metric_score  # noqa: F401
    # If we get here without ImportError, no circular import
