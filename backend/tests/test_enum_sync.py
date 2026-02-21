"""Backend-frontend enum sync — WELD_METRICS must match WeldMetric."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.shared_enums import WeldMetric


def test_weld_metrics_match_frontend():
    """Frontend WELD_METRICS (shared.ts) must equal backend WeldMetric.values."""
    shared_path = (
        Path(__file__).parent.parent.parent / "my-app" / "src" / "types" / "shared.ts"
    )
    assert shared_path.exists(), f"shared.ts not found: {shared_path}"
    content = shared_path.read_text()
    # Extract WELD_METRICS array: ["angle_consistency", ...] — supports double and single quotes
    match = re.search(
        r"WELD_METRICS:\s*WeldMetric\[\]\s*=\s*\[([^\]]+)\]",
        content,
        re.DOTALL,
    )
    assert match, (
        "WELD_METRICS array not found in shared.ts. "
        'Required format: WELD_METRICS: WeldMetric[] = ["val1", "val2", ...]'
    )
    raw = match.group(1)
    # Extract string values — supports both "x" and 'x'
    frontend_values = set(re.findall(r'["\']([^"\']+)["\']', raw))
    backend_values = {e.value for e in WeldMetric}
    assert frontend_values == backend_values, (
        f"WELD_METRICS mismatch: frontend {frontend_values} vs backend {backend_values}"
    )
