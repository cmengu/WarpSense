"""
Simulate real-time frame stream from aluminum mock sessions. Feeds AlertEngine.

Usage:
  python -m scripts.simulate_realtime --mode expert --output console --frames 100
  python -m scripts.simulate_realtime --mode novice --output websocket --frames 500
  python -m scripts.simulate_realtime --mode novice --loop --crash-at 50 --output console
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from data.mock_sessions import _generate_continuous_novice_frames, _generate_stitch_expert_frames
from realtime.alert_engine import AlertEngine
from realtime.alert_models import AlertPayload, FrameInput
from realtime.output_handler import handle_alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALERT_BASE_URL = "http://localhost:8000"


def _ns_asymmetry_from_frame(frame) -> float:
    """North minus south at 10mm. 0 if no thermal."""
    if not frame.thermal_snapshots:
        return 0.0
    snap = frame.thermal_snapshots[0]
    north = next((r.temp_celsius for r in snap.readings if r.direction == "north"), None)
    south = next((r.temp_celsius for r in snap.readings if r.direction == "south"), None)
    if north is None or south is None:
        return 0.0
    return north - south


def run_session(
    mode: str,
    output: str,
    frames_limit: int | None,
    crash_at: int | None,
    loop: bool,
    session_index: int = 0,
    suppression_ms_override: int | None = None,
) -> None:
    """Run one or more loop iterations."""
    while True:
        if mode == "expert":
            frames = _generate_stitch_expert_frames(session_index=session_index, num_frames=1500)
        else:
            frames = _generate_continuous_novice_frames(session_index=session_index, num_frames=1500)
        engine = AlertEngine(
            "config/alert_thresholds.json",
            suppression_ms_override=suppression_ms_override,
        )
        max_frames = frames_limit if frames_limit is not None else len(frames)
        for i, frame in enumerate(frames):
            if i >= max_frames:
                break
            if crash_at is not None and i == crash_at:
                logger.error("Crash at frame %d (--crash-at)", crash_at)
                raise RuntimeError("Simulated crash at frame %d" % crash_at)
            ns = _ns_asymmetry_from_frame(frame)
            travel_angle = frame.travel_angle_degrees
            travel_speed = frame.travel_speed_mm_per_min
            fin = FrameInput(
                frame_index=i,
                timestamp_ms=i * 10.0,  # 10ms per frame → 1500 frames = 15 simulated seconds
                travel_angle_degrees=travel_angle,
                travel_speed_mm_per_min=travel_speed,
                ns_asymmetry=ns,
                volts=frame.volts,
                amps=frame.amps,
            )
            alert = engine.push_frame(fin)
            if alert:
                handle_alert(alert, mode=output, base_url=ALERT_BASE_URL)
            if output == "websocket":
                if i % 3 == 0:
                    import requests
                    try:
                        requests.post(
                            f"{ALERT_BASE_URL}/internal/frame",
                            json={
                                "frame_index": i,
                                "ns_asymmetry": ns,
                                "travel_angle_degrees": travel_angle or 0,
                            },
                            timeout=1,
                        )
                    except Exception:
                        pass
        if not loop:
            break
        print("Restarting session", flush=True)
        logger.info("Restarting session")
        time.sleep(2)
        session_index += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate real-time weld frame stream")
    parser.add_argument("--mode", choices=["expert", "novice"], default="novice", help="Aluminum frame type")
    parser.add_argument("--frames", type=int, default=None, help="Stop after N frames. Default: full session")
    parser.add_argument("--output", choices=["console", "websocket"], default="console", help="Alert output")
    parser.add_argument("--loop", action="store_true", help="Restart from frame 0 on completion or crash")
    parser.add_argument("--crash-at", type=int, default=None, help="Raise exception at frame index (for preflight)")
    parser.add_argument("--session-index", type=int, default=0, help="Session index for reproducible mock data")
    parser.add_argument(
        "--suppression-ms",
        type=int,
        default=None,
        help="Override suppression_ms from alert_thresholds.json (e.g. 200 for preflight novice vs expert)",
    )
    args = parser.parse_args()
    try:
        run_session(
            mode=args.mode,
            output=args.output,
            frames_limit=args.frames,
            crash_at=args.crash_at,
            loop=args.loop,
            session_index=args.session_index,
            suppression_ms_override=args.suppression_ms,
        )
        return 0
    except Exception as e:
        logger.exception("Simulate failed: %s", e)
        if args.loop:
            print("Restarting session", flush=True)
            logger.info("Restarting session")
            time.sleep(2)
            return main()
        return 1


if __name__ == "__main__":
    sys.exit(main())
