"""
Runs import-linter against backend/.importlinter so architecture contracts
fail the suite, not just a separate CI step. See .importlinter for the
contract list; each mirrors a folder-README invariant.
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def test_import_contracts_hold():
    # Subprocess (not in-process API) so grimp's import graph is built from a
    # clean interpreter, unaffected by whatever the test run already imported.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports; raise SystemExit(lint_imports())",
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    assert "Contracts:" in result.stdout, (
        f"import-linter did not run:\n{result.stdout}\n{result.stderr}"
    )
    assert result.returncode == 0, (
        "import-linter found architecture violations:\n"
        f"{result.stdout}\n{result.stderr}"
    )
