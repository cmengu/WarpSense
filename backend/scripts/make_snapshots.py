"""
Stage 0 snapshot harness.

Freezes the observable behavior of every deterministic pipeline layer as
committed golden files under tests/snapshots/, BEFORE the warpsense/ package
refactor. The refactor's "pure move" PR must leave every file here untouched;
a deliberate behavior change must arrive with a --write bless in its own
commit, so the numeric drift is reviewed in the PR diff like code.

What is captured (per corpus archetype):
  frames.json                 head/tail sample + sha256 of the full canonical
                              frame dump (catches generator drift, keeps repo lean)
  floor_features.json         features/extractor.extract_features_for_frames
  floor_rules.json            scoring/rule_based.score_session      (sessions only)
  floor_windowed.json         scoring/rule_based.score_frames_windowed (sessions only)
  classifier_features.json    features/session_feature_extractor (the 11)
  classifier_prediction.json  WeldClassifier.predict via warpsense/classifier/weld_classifier.joblib
  warp_features.json          features/warp_features (the 8) on the last-50 window
  warp_risk.json              services/prediction_service.predict_warp_risk
  wqi_decomposed.json         scoring/scorer alerts + decomposed WQI (per component)
  report_summary.json         scoring/report_summary.compute_report_summary
plus scenarios/<id>.json      classifier prediction for each eval scenario
                              (this is also the frozen INPUT to the LLM agent
                              layer, which is deliberately not snapshotted)
and manifest.json             package versions + sha256 of the model artifact
                              and config files, so any diff can first answer
                              "same environment?"

Determinism contract:
  - PYTHONHASHSEED is pinned to 0 as a guard. Generator seeding became
    hash-independent (zlib.crc32) in PR 2; the pin stays so any future
    hash(...)-derived nondeterminism fails loudly here instead of drifting.
  - Volatile wall-clock fields are scrubbed by key name (SCRUB_KEYS below).
  - Floats are serialized at full repr precision; NaN/Inf become strings.

Usage (from backend/):
  venv/bin/python scripts/make_snapshots.py --check           # compare vs goldens
  venv/bin/python scripts/make_snapshots.py --write           # bless new goldens
  venv/bin/python scripts/make_snapshots.py --write --out DIR # write elsewhere
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import date, datetime
from enum import Enum
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = BACKEND / "tests" / "snapshots"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Wall-clock fields replaced with a sentinel wherever they appear.
# Every entry names its source so additions stay deliberate:
#   start_time / completed_at  — datetime.now() in data/mock_sessions.py Session constructors
#   computed_at_ms             — time.time() in scoring/scorer.py DecomposedSessionScore
#   generated_at               — datetime.now() in scoring/report_summary.py
SCRUB_KEYS = frozenset({"start_time", "completed_at", "computed_at_ms", "generated_at"})
SCRUBBED = "__SCRUBBED__"

HASHED_ARTIFACTS = (
    "warpsense/classifier/weld_classifier.joblib",
    "warpsense/config/scoring_config.json",
    "warpsense/config/alert_thresholds.json",
    "warpsense/config/report_thresholds.json",
)


def _require_fixed_hashseed() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0" or sys.flags.hash_randomization:
        raise RuntimeError(
            "Snapshots require PYTHONHASHSEED=0 (precautionary determinism guard). "
            "Run via the CLI, which re-execs itself, or export PYTHONHASHSEED=0 "
            "before starting Python."
        )


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------

def canonicalize(obj):
    """Recursively convert to JSON-safe primitives with a fixed policy."""
    import numpy as np
    from pydantic import BaseModel

    if isinstance(obj, BaseModel):
        return canonicalize(obj.model_dump(mode="python"))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return canonicalize(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {
            str(k): (SCRUBBED if str(k) in SCRUB_KEYS else canonicalize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [canonicalize(v) for v in obj]
    if isinstance(obj, Enum):
        return canonicalize(obj.value)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return canonicalize(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        obj = float(obj)
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    raise TypeError(f"Unsupported type in snapshot: {type(obj)!r}")


def dumps_canonical(obj) -> str:
    return json.dumps(canonicalize(obj), sort_keys=True, indent=1, allow_nan=False) + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Snapshot builders
# ---------------------------------------------------------------------------

def _load_classifier():
    import joblib
    from warpsense.classifier.weld_classifier import WeldClassifier

    saved = joblib.load(BACKEND / "warpsense" / "classifier" / "weld_classifier.joblib")
    clf = WeldClassifier()
    clf._model = saved["model"]
    clf._classes = saved["classes"]
    return clf


def _corpus():
    """(name, frames, session_or_None, process_type). Fixed seeds; large session
    omitted — it reuses the expert signal functions, adding runtime, not coverage."""
    from data.mock_sessions import (
        _generate_aluminium_parametric_frames,
        _generate_continuous_novice_frames,
        _generate_stitch_expert_frames,
        generate_expert_session,
        generate_novice_session,
    )

    expert = generate_expert_session()
    novice = generate_novice_session()
    return [
        ("expert", expert.frames, expert, expert.weld_type),
        ("novice", novice.frames, novice, novice.weld_type),
        ("stitch_expert_s0", _generate_stitch_expert_frames(0, 1500), None, "aluminum"),
        ("continuous_novice_s0", _generate_continuous_novice_frames(0, 1500), None, "aluminum"),
        ("al_nominal_s0", _generate_aluminium_parametric_frames("al_nominal", 0, 1500), None, "aluminum"),
        ("al_defective_s0", _generate_aluminium_parametric_frames("al_defective", 0, 1500), None, "aluminum"),
    ]


def build_snapshots() -> dict[str, str]:
    """Return {relative_path: canonical_json_text} for the whole snapshot tree."""
    _require_fixed_hashseed()

    from evals.eval_scenarios import SCENARIOS
    from warpsense.features.extractor import extract_features_for_frames
    from warpsense.features.session_feature_extractor import SessionFeatureExtractor
    from warpsense.features.warp_features import extract_features as warp_extract_features
    from warpsense.features.warp_features import features_to_array
    from warpsense.floor.report_summary import compute_report_summary
    from warpsense.floor.rule_based import score_frames_windowed, score_session
    from warpsense.floor.scorer import _build_alerts_from_frames, score_session_decomposed
    from warpsense.services.prediction_service import predict_warp_risk

    clf = _load_classifier()
    extractor = SessionFeatureExtractor()
    out: dict[str, str] = {}

    for name, frames, session, process_type in _corpus():
        base = f"sessions/{name}"
        frames_text = dumps_canonical(frames)
        out[f"{base}/frames.json"] = dumps_canonical(
            {
                "frame_count": len(frames),
                "canonical_sha256": _sha256_text(frames_text),
                "head": frames[:3],
                "tail": frames[-3:],
            }
        )

        floor_features = extract_features_for_frames(frames)
        out[f"{base}/floor_features.json"] = dumps_canonical(floor_features)

        frames_dicts = [f.model_dump(mode="python") for f in frames]
        session_features = extractor.extract(name, frames_dicts)
        out[f"{base}/classifier_features.json"] = dumps_canonical(session_features)
        out[f"{base}/classifier_prediction.json"] = dumps_canonical(
            clf.predict(session_features)
        )

        window = frames_dicts[-50:]
        warp_features = warp_extract_features(window)
        out[f"{base}/warp_features.json"] = dumps_canonical(
            {"features": warp_features, "array": features_to_array(warp_features)}
        )
        out[f"{base}/warp_risk.json"] = dumps_canonical(predict_warp_risk(window))

        alerts = _build_alerts_from_frames(frames)
        wqi = score_session_decomposed(frames, alerts, session_id=name)
        out[f"{base}/wqi_decomposed.json"] = dumps_canonical(
            {"alerts": alerts, "score": wqi}
        )
        out[f"{base}/report_summary.json"] = dumps_canonical(
            compute_report_summary(name, frames, alerts, process_type)
        )

        if session is not None:
            out[f"{base}/floor_rules.json"] = dumps_canonical(
                score_session(session, floor_features, None)
            )
            metadata = {
                "weld_type": session.weld_type,
                "thermal_sample_interval_ms": session.thermal_sample_interval_ms,
                "thermal_directions": session.thermal_directions,
                "thermal_distance_interval_mm": session.thermal_distance_interval_mm,
                "sensor_sample_rate_hz": session.sensor_sample_rate_hz,
            }
            out[f"{base}/floor_windowed.json"] = dumps_canonical(
                score_frames_windowed(session.frames, None, metadata)
            )

    for sc in SCENARIOS:
        out[f"scenarios/{sc.scenario_id}.json"] = dumps_canonical(
            {"features": sc.features, "prediction": clf.predict(sc.features)}
        )

    out["manifest.json"] = dumps_canonical(_manifest(len(out)))
    return out


def _manifest(file_count: int) -> dict:
    import joblib
    import numpy
    import pandas
    import pydantic
    import sklearn

    return {
        "spec_version": 1,
        "python": ".".join(str(v) for v in sys.version_info[:3]),
        "pythonhashseed": "0",
        "packages": {
            "joblib": joblib.__version__,
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "pydantic": pydantic.VERSION,
            "scikit-learn": sklearn.__version__,
        },
        "artifact_sha256": {rel: _sha256_file(BACKEND / rel) for rel in HASHED_ARTIFACTS},
        "scrub_keys": sorted(SCRUB_KEYS),
        "snapshot_file_count": file_count,
    }


# ---------------------------------------------------------------------------
# Write / check
# ---------------------------------------------------------------------------

def _on_disk(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        str(p.relative_to(root)): p
        for p in sorted(root.rglob("*.json"))
    }


def write_snapshots(root: Path, force: bool = False) -> None:
    if root == SNAPSHOT_ROOT and not force:
        try:
            dirty = subprocess.run(
                ["git", "status", "--porcelain", "--", str(root)],
                cwd=BACKEND, capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            dirty = ""
        if dirty:
            raise SystemExit(
                "tests/snapshots has uncommitted changes — commit or discard them "
                "first so a bless is always its own reviewable commit (or use --force)."
            )

    built = build_snapshots()
    for rel, path in _on_disk(root).items():
        if rel not in built:
            path.unlink()
    for rel, text in sorted(built.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(f"wrote {len(built)} snapshot files to {root}")


def check_snapshots(root: Path, max_diff_lines: int = 12) -> list[str]:
    """Return human-readable mismatch reports; empty list means identical."""
    import difflib

    built = build_snapshots()
    disk = _on_disk(root)
    problems: list[str] = []

    for rel in sorted(set(built) - set(disk)):
        problems.append(f"MISSING on disk: {rel}")
    for rel in sorted(set(disk) - set(built)):
        problems.append(f"EXTRA on disk (not generated anymore): {rel}")

    for rel in sorted(set(built) & set(disk)):
        old = disk[rel].read_text()
        if old == built[rel]:
            continue
        diff = list(
            difflib.unified_diff(
                old.splitlines(), built[rel].splitlines(),
                fromfile=f"golden/{rel}", tofile=f"current/{rel}", lineterm="", n=1,
            )
        )
        shown = "\n".join(diff[:max_diff_lines])
        more = len(diff) - max_diff_lines
        if more > 0:
            shown += f"\n... ({more} more diff lines)"
        problems.append(f"CHANGED: {rel}\n{shown}")

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate golden files")
    mode.add_argument("--check", action="store_true", help="compare against golden files")
    parser.add_argument("--out", type=Path, default=SNAPSHOT_ROOT,
                        help="snapshot directory (default: tests/snapshots)")
    parser.add_argument("--force", action="store_true",
                        help="allow --write over uncommitted snapshot changes")
    args = parser.parse_args()

    if args.write:
        write_snapshots(args.out, force=args.force)
        return

    problems = check_snapshots(args.out)
    if not problems:
        print(f"OK: snapshots in {args.out} match current behavior")
        return
    print(f"SNAPSHOT MISMATCH — {len(problems)} file(s) differ from {args.out}:\n")
    print("\n\n".join(problems))
    print(
        "\nIf this change is intentional, bless it in its own commit:\n"
        "  venv/bin/python scripts/make_snapshots.py --write"
    )
    raise SystemExit(1)


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0" or sys.flags.hash_randomization:
        os.execve(
            sys.executable,
            [sys.executable, os.path.abspath(__file__), *sys.argv[1:]],
            {**os.environ, "PYTHONHASHSEED": "0"},
        )
    main()
