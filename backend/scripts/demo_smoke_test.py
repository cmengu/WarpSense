"""
Demo smoke test — runs the full demo flow N times and reports pass/fail.

Usage (from backend/):
    python -m scripts.demo_smoke_test
    python -m scripts.demo_smoke_test --runs 20 --base-url http://localhost:8000

Exit 0 if all pass, 1 if any fail.
"""
import argparse
import json
import sys
import time
import urllib.request

_DEFAULT_SESSION = "sess_novice_aluminium_001_001"
_DEFAULT_URL = "http://localhost:8000"


def check_health(base: str) -> bool:
    try:
        r = urllib.request.urlopen(f"{base}/api/health/warp", timeout=5)
        data = json.loads(r.read())
        return bool(data.get("classifier_initialised") and data.get("graph_initialised"))
    except Exception as e:
        print(f"  health check failed: {e}")
        return False


def run_analysis_stream(base: str, session_id: str) -> bool:
    req = urllib.request.Request(
        f"{base}/api/sessions/{session_id}/analyse",
        method="POST",
        headers={"Accept": "text/event-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                evt = json.loads(line[5:].strip())
                if evt.get("stage") == "complete":
                    return "report" in evt
                if evt.get("stage") == "error":
                    print(f"  SSE error: {evt.get('message')}")
                    return False
    except Exception as e:
        print(f"  stream error: {e}")
        return False
    return False


def fetch_report(base: str, session_id: str) -> bool:
    try:
        r = urllib.request.urlopen(
            f"{base}/api/sessions/{session_id}/reports", timeout=10
        )
        data = json.loads(r.read())
        return "disposition" in data and "rework_cost_usd" in data
    except Exception as e:
        print(f"  report fetch failed: {e}")
        return False


def run_simulator(base: str) -> bool:
    body = json.dumps({
        "heat_input_level": 2200,
        "torch_angle_deviation": 22,
        "arc_stability": 0.48,
    }).encode()
    req = urllib.request.Request(
        f"{base}/api/simulator/predict",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        data = json.loads(r.read())
        return "rework_cost_usd" in data and data.get("quality_class") in ("DEFECTIVE", "MARGINAL")
    except Exception as e:
        print(f"  simulator failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--base-url", default=_DEFAULT_URL)
    parser.add_argument("--session-id", default=_DEFAULT_SESSION)
    args = parser.parse_args()

    print(f"Demo smoke test: {args.runs} runs — {args.base_url}")
    print("-" * 50)

    if not check_health(args.base_url):
        print("ABORT: Backend not healthy")
        sys.exit(1)
    print("PASS health check")

    results: list[bool] = []
    for i in range(1, args.runs + 1):
        t0 = time.monotonic()
        ok_stream = run_analysis_stream(args.base_url, args.session_id)
        ok_report = fetch_report(args.base_url, args.session_id) if ok_stream else False
        ok_sim = run_simulator(args.base_url)
        elapsed = time.monotonic() - t0
        passed = ok_stream and ok_report and ok_sim
        results.append(passed)
        status = "PASS" if passed else "FAIL"
        print(
            f"  Run {i:02d}/{args.runs}: {status}"
            f"  stream={ok_stream} report={ok_report} sim={ok_sim}"
            f"  {elapsed:.1f}s"
        )

    print("-" * 50)
    passed_count = sum(results)
    print(f"Results: {passed_count}/{args.runs} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
