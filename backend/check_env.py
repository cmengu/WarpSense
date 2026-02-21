#!/usr/bin/env python3
"""
Pre-flight script for WarpSense AI demo. Run the night before demo day.

Checks: Cactus import (or stub), weights path, GEMINI_API_KEY, POST /api/ai/analyze,
two concurrent POSTs, all 5 scenarios end-to-end.

Exit 0 if all pass; exit 1 with clear failure message.
"""

import json
import os
import sys
import threading
from pathlib import Path

# Add backend to path
_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"  ✗ {msg}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def check_cactus_import() -> bool:
    """Cactus import or stub — demo must run either way."""
    try:
        from function_gemma import generate_hybrid
        from warp_tools import WARP_TOOLS
        # Quick smoke test
        r = generate_hybrid([{"role": "user", "content": "voltage 28V"}], WARP_TOOLS)
        if "source" in r:
            ok("Cactus/stub import and generate_hybrid work")
            return True
        fail("generate_hybrid returned no source")
        return False
    except Exception as e:
        fail(f"Cactus/stub import failed: {e}")
        return False


def check_weights_path() -> bool:
    """Weights path exists (optional when stub)."""
    weights = _BACKEND / "cactus" / "weights" / "functiongemma-270m-it"
    if weights.exists():
        ok(f"Weights path exists: {weights}")
        return True
    # Stub mode: weights not required
    ok("Weights path not found (stub mode — OK)")
    return True


def check_gemini_key() -> bool:
    """GEMINI_API_KEY set (optional for on-device-only)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        ok("GEMINI_API_KEY set")
        return True
    ok("GEMINI_API_KEY unset (cloud path will return cloud_error — OK for stub demo)")
    return True


def check_post_analyze(base_url: str = "http://localhost:8000") -> bool:
    """POST /api/ai/analyze returns 200."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/api/ai/analyze",
            data=b'{"query":"voltage 28V"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                ok("POST /api/ai/analyze returns 200")
                return True
            fail(f"POST /api/ai/analyze returned {resp.status}")
            return False
    except Exception as e:
        fail(f"POST /api/ai/analyze failed: {e}. Is the server running? (uvicorn main:app)")
        return False


def check_concurrent_posts(base_url: str = "http://localhost:8000") -> bool:
    """Two concurrent POSTs both complete."""
    results = [None, None]

    def do_post(i: int) -> None:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{base_url}/api/ai/analyze",
                data=b'{"query":"angle 52"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                results[i] = resp.status == 200
        except Exception:
            results[i] = False

    t1 = threading.Thread(target=do_post, args=(0,))
    t2 = threading.Thread(target=do_post, args=(1,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    if results[0] and results[1]:
        ok("Two concurrent POSTs both completed")
        return True
    fail("Concurrent POSTs failed")
    return False


def check_all_scenarios(base_url: str = "http://localhost:8000") -> bool:
    """All 5 scenarios run end-to-end."""
    scenarios = [
        "voltage is 28V, range 18-24",
        "angle 52 degrees, max 45",
        "session WS-042 scored 41, why?",
        "Analyze session WS-042 — check score, then parameters, then flag any issues",
        "wire_feed is 12, range 10-15",
    ]
    try:
        import urllib.request
        for i, q in enumerate(scenarios):
            req = urllib.request.Request(
                f"{base_url}/api/ai/analyze",
                data=json.dumps({"query": q}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    fail(f"Scenario {i+1} returned {resp.status}")
                    return False
        ok("All 5 scenarios completed")
        return True
    except Exception as e:
        fail(f"Scenarios failed: {e}")
        return False


def main() -> int:
    print("WarpSense AI pre-flight checks\n")
    check_cactus_import()
    check_weights_path()
    check_gemini_key()
    print()
    check_post_analyze()
    check_concurrent_posts()
    check_all_scenarios()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s) failed.")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
