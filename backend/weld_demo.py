#!/usr/bin/env python3
"""
WarpSense AI demo script. Runs 5 scenarios without UI.

Works from project root: python backend/weld_demo.py
Works from backend: cd backend && python weld_demo.py

--offline: Zero network. Cloud-bound queries return canned offline message.
"""

import argparse
import os
import sys

_DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
if _DEMO_DIR not in sys.path:
    sys.path.insert(0, _DEMO_DIR)

try:
    from warp_tools import WARP_TOOLS
    from function_gemma import generate_hybrid
except Exception as e:
    print("Cactus not available — run Step 1 first.")
    print(f"Error: {e}")
    sys.exit(1)


def run(label: str, query: str, offline: bool = False) -> tuple[str, float]:
    """Run one scenario; print SOURCE, TIME, TEXT, TOOL, ARGS, privacy. Returns (source, time_ms)."""
    result = generate_hybrid(
        [{"role": "user", "content": query}], WARP_TOOLS, offline=offline
    )
    source = result.get("source", "")
    time_ms = result.get("total_time_ms", 0) or 0

    # Privacy narrative (Step 6b)
    if source == "on-device" or source.startswith("on-device"):
        print("  [ON-DEVICE] Sensor data never left the device.")
    elif source == "cloud":
        print("  [CLOUD] Anonymized query only — no raw sensor values transmitted.")
    elif source == "offline":
        print("  [OFFLINE] No network — canned response.")
    elif "cloud" in source:
        print("  [CLOUD] Anonymized query only — no raw sensor values transmitted.")

    print(f"  SOURCE : {source}")
    print(f"  TIME   : {time_ms:.0f}ms")
    if result.get("text"):
        t = result["text"]
        print(f"  TEXT   : {t[:200]}{'...' if len(t) > 200 else ''}")
    for call in result.get("function_calls", []):
        print(f"  TOOL   : {call['name']}")
        print(f"  ARGS   : {call.get('arguments', {})}")
    if not result.get("function_calls") and not result.get("text"):
        print("  TOOL   : (none)")
    return (source, time_ms)


def main() -> None:
    parser = argparse.ArgumentParser(description="WarpSense AI demo — 5 scenarios")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Zero network. Cloud-bound queries return canned offline message.",
    )
    args = parser.parse_args()
    offline = args.offline

    if offline:
        print("OFFLINE MODE — Zero network calls. Welding shop floors have poor connectivity.")
        print()

    scenarios = [
        ("Scenario 1: On-device (voltage)", "voltage is 28V, range 18-24"),
        ("Scenario 2: On-device (angle)", "angle 52 degrees, max 45"),
        ("Scenario 3: Cloud (coaching)", "session WS-042 scored 41, why?"),
        ("Scenario 4: Chained (evaluate→check→flag)", "Analyze session WS-042 — check score, then parameters, then flag any issues"),
        ("Scenario 5: Escalation", "wire_feed is 12, range 10-15"),  # hallucinated param -> validation fails
    ]

    on_device_times: list[float] = []
    cloud_time: float | None = None
    for label, query in scenarios:
        print(f"\n{label}")
        print(f"  QUERY  : {query}")
        source, time_ms = run(label, query, offline=offline)
        if source == "on-device" and time_ms > 0:
            on_device_times.append(time_ms)
        elif source == "cloud" and time_ms > 0:
            cloud_time = time_ms

    # Latency comparison: Nx faster on-device (from real ms, never hardcoded)
    if on_device_times and cloud_time and not offline:
        avg_on_device = sum(on_device_times) / len(on_device_times)
        if cloud_time > avg_on_device:
            n = cloud_time / avg_on_device
            print(f"\n[LATENCY] On-device avg: {avg_on_device:.0f}ms, Cloud: {cloud_time:.0f}ms → {n:.1f}x faster on-device")


if __name__ == "__main__":
    main()
