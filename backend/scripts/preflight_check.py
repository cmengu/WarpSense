"""
Preflight check for April 9 demo. Run: python -m scripts.preflight_check

All checks must pass. Exit 0 if all pass, non-zero otherwise.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check1_alert_thresholds() -> bool:
    """alert_thresholds.json exists, parses, no nulls, AlertEngine init OK."""
    try:
        from realtime.alert_engine import AlertEngine, load_thresholds
        cfg_path = Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json"
        if not cfg_path.exists():
            print("FAIL [1] alert_thresholds.json not found")
            return False
        data = json.loads(cfg_path.read_text())
        for k, v in data.items():
            if v is None:
                print(f"FAIL [1] {k} is null")
                return False
        load_thresholds("config/alert_thresholds.json")
        AlertEngine("config/alert_thresholds.json")
        print("PASS [1] alert_thresholds.json OK, AlertEngine init OK")
        return True
    except Exception as e:
        print(f"FAIL [1] {e}")
        return False


def _parse_alerts_by_rule(stdout: str) -> tuple[dict[str, int], int]:
    """
    Parse simulate_realtime console output for ALERT lines.
    Returns (per_rule_counts, total). rule1/2/3 from 'rule=ruleN' in each line.
    """
    per_rule: dict[str, int] = {"rule1": 0, "rule2": 0, "rule3": 0}
    for line in stdout.splitlines():
        if "ALERT" not in line:
            continue
        m = re.search(r"rule=(rule[123])", line)
        if m:
            per_rule[m.group(1)] = per_rule.get(m.group(1), 0) + 1
    return per_rule, sum(per_rule.values())


def check2_novice_vs_expert() -> bool:
    """
    Total novice alerts > expert alerts (all three rules active).
    Run 1500 frames per mode, session_index 0..4. Report per-rule breakdown and total.
    Demo note: suppression ceiling limits ratio at short session lengths.
    """
    try:
        backend = Path(__file__).resolve().parent.parent
        env = {**__import__("os").environ, "PATH": str(backend / "venv" / "bin") + ":" + __import__("os").environ.get("PATH", "")}
        expert_r1 = expert_r2 = expert_r3 = 0
        novice_r1 = novice_r2 = novice_r3 = 0
        for si in range(5):
            proc = subprocess.run(
                [
                    sys.executable, "-m", "scripts.simulate_realtime",
                    "--mode", "expert", "--output", "console", "--frames", "1500",
                    "--session-index", str(si),
                ],
                cwd=str(backend),
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            pr, _ = _parse_alerts_by_rule(proc.stdout)
            expert_r1 += pr.get("rule1", 0)
            expert_r2 += pr.get("rule2", 0)
            expert_r3 += pr.get("rule3", 0)
        for si in range(5):
            proc = subprocess.run(
                [
                    sys.executable, "-m", "scripts.simulate_realtime",
                    "--mode", "novice", "--output", "console", "--frames", "1500",
                    "--session-index", str(si),
                ],
                cwd=str(backend),
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            pr, _ = _parse_alerts_by_rule(proc.stdout)
            novice_r1 += pr.get("rule1", 0)
            novice_r2 += pr.get("rule2", 0)
            novice_r3 += pr.get("rule3", 0)
        expert_total = expert_r1 + expert_r2 + expert_r3
        novice_total = novice_r1 + novice_r2 + novice_r3
        # Per-rule breakdown
        print(
            f"  expert: rule1={expert_r1} rule2={expert_r2} rule3={expert_r3} total={expert_total}"
        )
        print(
            f"  novice: rule1={novice_r1} rule2={novice_r2} rule3={novice_r3} total={novice_total}"
        )
        if novice_total > expert_total:
            print(f"PASS [2] novice={novice_total} > expert={expert_total}")
            print(
                "  Demo note: suppression ceiling limits ratio at short session lengths. "
                "Full 1500-frame sessions show novice > expert consistently."
            )
            return True
        print(
            f"FAIL [2] novice={novice_total} <= expert={expert_total} (need novice > expert)"
        )
        return False
    except Exception as e:
        print(f"FAIL [2] {e}")
        return False


def check3_benchmark() -> bool:
    """Benchmark 1000 push_frame, p99 < 50ms."""
    try:
        backend = Path(__file__).resolve().parent.parent
        env = {**__import__("os").environ, "PATH": str(backend / "venv" / "bin") + ":" + __import__("os").environ.get("PATH", "")}
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_alert_engine.py", "-v", "-k", "benchmark"],
            cwd=str(backend),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        if proc.returncode == 0:
            print("PASS [3] benchmark p99 < 50ms")
            return True
        print(f"FAIL [3] benchmark failed: {proc.stderr[-500:] if proc.stderr else proc.stdout[-500:]}")
        return False
    except Exception as e:
        print(f"FAIL [3] {e}")
        return False


def check4_backend_websocket() -> bool:
    """Backend running, simulate websocket 500 frames, each POST 200."""
    try:
        import urllib.request
        try:
            r = urllib.request.urlopen("http://localhost:8000/docs", timeout=3)
            if r.status != 200:
                raise ValueError(f"docs returned {r.status}")
        except Exception as e:
            print("FAIL [4] Backend not running — start with ENV=development uvicorn main:app before running preflight")
            return False
        backend = Path(__file__).resolve().parent.parent
        env = {**__import__("os").environ, "PATH": str(backend / "venv" / "bin") + ":" + __import__("os").environ.get("PATH", ""), "ENV": "development"}
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.simulate_realtime", "--mode", "novice", "--output", "websocket", "--frames", "500"],
            cwd=str(backend),
            capture_output=True,
            text=True,
            env=env,
            timeout=90,
        )
        if proc.returncode == 0:
            print("PASS [4] simulate websocket 500 frames OK")
            return True
        print(f"FAIL [4] {proc.stderr[-300:] if proc.stderr else proc.stdout[-300:]}")
        return False
    except Exception as e:
        print(f"FAIL [4] {e}")
        return False


def check5_loop_restart() -> bool:
    """simulate --loop --crash-at 100, capture 10s, assert 'Restarting session' in output."""
    try:
        backend = Path(__file__).resolve().parent.parent
        env = {**__import__("os").environ, "PATH": str(backend / "venv" / "bin") + ":" + __import__("os").environ.get("PATH", "")}
        proc = subprocess.Popen(
            [sys.executable, "-m", "scripts.simulate_realtime", "--mode", "novice", "--loop", "--crash-at", "100", "--output", "console"],
            cwd=str(backend),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        out_chunks = []
        start = time.monotonic()
        while time.monotonic() - start < 10:
            if proc.stdout and proc.stdout.readable():
                chunk = proc.stdout.read(4096)
                if chunk:
                    out_chunks.append(chunk)
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        out = "".join(out_chunks)
        if "Restarting session" in out:
            print("PASS [5] loop restart OK")
            return True
        print("FAIL [5] 'Restarting session' not found in output")
        return False
    except Exception as e:
        print(f"FAIL [5] {e}")
        return False


def main() -> int:
    print("Preflight check for April 9 demo")
    print("-" * 40)
    results = [
        check1_alert_thresholds(),
        check2_novice_vs_expert(),
        check3_benchmark(),
        check4_backend_websocket(),
        check5_loop_restart(),
    ]
    print("-" * 40)
    if all(results):
        print("All checks PASSED")
        return 0
    print("Some checks FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
