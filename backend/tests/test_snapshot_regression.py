"""
Snapshot regression test — Stage 0 of the warpsense/ refactor.

Regenerates every snapshot in a fresh subprocess (mirroring a clean-checkout
CI run) and byte-compares against the committed goldens in tests/snapshots/.
A mismatch fails with the harness's unified diff naming the exact fields.

Intentional behavior changes are blessed in their own commit via:
    venv/bin/python scripts/make_snapshots.py --write
so the numeric drift is reviewed in the PR diff like code.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SNAPSHOTS = BACKEND / "tests" / "snapshots"
SCRIPT = BACKEND / "scripts" / "make_snapshots.py"


def test_goldens_are_committed_and_nontrivial():
    """Guards against --check passing vacuously over an empty/truncated dir."""
    assert (SNAPSHOTS / "manifest.json").is_file(), (
        "tests/snapshots/manifest.json missing — generate goldens with "
        "scripts/make_snapshots.py --write"
    )
    files = list(SNAPSHOTS.rglob("*.json"))
    assert len(files) >= 70, (
        f"only {len(files)} snapshot files under tests/snapshots — "
        "golden set looks truncated"
    )


def test_current_behavior_matches_goldens():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )
    assert proc.returncode == 0, (
        "Pipeline behavior diverged from committed snapshots. If the change "
        "is intentional, bless it with make_snapshots.py --write in its own "
        "commit. Otherwise a refactor step altered behavior:\n\n"
        + proc.stdout[-8000:]
        + ("\n[stderr]\n" + proc.stderr[-2000:] if proc.stderr.strip() else "")
    )
