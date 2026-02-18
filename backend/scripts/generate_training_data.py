"""
Generates training_data.csv for warp prediction model.

Feature vector per frame (rolling 50-frame window):
  angle_mean, angle_std, amps_mean, amps_std, volts_mean,
  temp_current, thermal_asymmetry, thermal_asymmetry_delta

Label: will_breach = 1 if thermal asymmetry >= 20°C within next 30 frames, else 0

Usage:
  python -m backend.scripts.generate_training_data --output data/training_data.csv

MUST run from project root (cwd must be workspace root).
Reproducible: random.seed(42) ensures same CSV across runs.
"""
import argparse
import csv
import random
import sys
from pathlib import Path

random.seed(42)

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from data.mock_sessions import generate_session_for_welder
from data.mock_welders import WELDER_ARCHETYPES
from features.warp_features import extract_asymmetry, extract_features, FEATURE_COLS

WINDOW_SIZE = 50
LOOKAHEAD_FRAMES = 30
THERMAL_BREACH_CELSIUS = 20.0


def compute_labels(frames: list[dict]) -> list[int]:
    """Returns 1 if asymmetry breach within LOOKAHEAD_FRAMES, else 0."""
    labels = []
    for i in range(len(frames)):
        lookahead = frames[i : i + LOOKAHEAD_FRAMES]
        breach = any(
            extract_asymmetry(f) >= THERMAL_BREACH_CELSIUS for f in lookahead
        )
        labels.append(1 if breach else 0)
    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/training_data.csv")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate mock data structure only; no CSV output",
    )
    args = parser.parse_args()

    # Assert cwd is project root — output path and provenance are relative to cwd
    cwd = Path.cwd()
    if not (cwd / "backend").is_dir() or not (cwd / "backend" / "data").exists():
        raise RuntimeError(
            f"Must run from project root (cwd={cwd}). Run: python -m backend.scripts.generate_training_data"
        )

    for welder in WELDER_ARCHETYPES:
        if welder.get("sessions", 0) < 1:
            raise ValueError(
                f"WELDER_ARCHETYPES entry {welder.get('welder_id', '?')} has sessions < 1"
            )

    rows = []
    for welder in WELDER_ARCHETYPES:
        for session_idx in range(welder["sessions"]):
            sid = f"sess_{welder['welder_id']}_{session_idx + 1:03d}"
            session = generate_session_for_welder(
                welder["welder_id"], welder["arc"], session_idx, sid
            )
            frames = [f.model_dump() for f in session.frames]
            labels = compute_labels(frames)

            for i in range(WINDOW_SIZE, len(frames)):
                window = frames[i - WINDOW_SIZE : i]
                features = extract_features(window, frames[i])
                features["will_breach"] = labels[i]
                rows.append(features)

    if args.validate_only:
        if len(rows) == 0:
            raise ValueError("No training rows — check WINDOW_SIZE and session lengths")
        pos_count = sum(r["will_breach"] for r in rows)
        rate = pos_count / len(rows)
        print(f"Validation OK: {len(rows)} samples, positive rate {rate:.2%}")
        return

    if len(rows) == 0:
        raise ValueError(
            "No training rows generated — check WINDOW_SIZE and session lengths"
        )

    pos_count = sum(r["will_breach"] for r in rows)
    min_per_class = min(pos_count, len(rows) - pos_count)
    if min_per_class < 2:
        raise ValueError(
            f"stratify requires min 2 per class; got {pos_count} positives, {len(rows)-pos_count} negatives"
        )

    out_path = Path(args.output)
    out_parent = out_path.parent
    if out_parent.exists() and not out_parent.is_dir():
        raise FileExistsError(f"Output parent {out_parent} exists but is not a directory")
    out_parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(FEATURE_COLS) + ["will_breach"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    rate = pos_count / len(rows)
    print(f"Generated {len(rows)} samples. Positive rate: {rate:.2%}")
    if rate < 0.10 or rate > 0.40:
        print("WARNING: Positive rate outside 10–40%")
    if rate < 0.05:
        raise ValueError(f"Positive rate {rate:.2%} too low — model biased")


if __name__ == "__main__":
    main()
