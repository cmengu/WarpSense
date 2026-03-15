"""
WarpSense -- End-to-End Demo Runner
backend/run_warpsense_agent.py

One command. Full pipeline output.

    python run_warpsense_agent.py                  # run all 10 sessions
    python run_warpsense_agent.py --session WS-003  # single session
    python run_warpsense_agent.py --worst           # only MARGINAL sessions
    python run_warpsense_agent.py --no-build-kb     # skip KB rebuild

Pipeline per session:
    SessionFeatures -> WeldClassifier -> WeldPrediction -> WarpSenseAgent -> WeldQualityReport
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # repo root .env

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from features.session_feature_extractor import generate_feature_dataset, SessionFeatures
from features.weld_classifier import WeldClassifier
from agent.warpsense_agent import WarpSenseAgent


def ensure_kb_exists(force_rebuild=False):
    kb_path = _ROOT / "knowledge" / "chroma_db"
    if not force_rebuild and kb_path.exists() and any(kb_path.iterdir()):
        print(f"[Runner] KB exists. Skipping rebuild. (--rebuild-kb to force)")
        return
    print("[Runner] Building knowledge base...")
    try:
        from knowledge.build_welding_kb import build_knowledge_base
        build_knowledge_base(persist=True, verbose=True)
    except ImportError as e:
        print(f"[Runner] ERROR: {e}")
        sys.exit(1)


def run_pipeline(session_ids=None, only_marginal=False, verbose_agent=True):
    print("\n" + "=" * 58)
    print("WARPSENSE -- FULL PIPELINE RUN")
    print("=" * 58)

    print("\n[Phase 1] Generating feature dataset...")
    all_features = generate_feature_dataset()
    print(f"  -> {len(all_features)} sessions generated")

    if session_ids:
        all_features = [f for f in all_features if f.session_id in session_ids]
        if not all_features:
            print(f"ERROR: No sessions found matching: {session_ids}")
            sys.exit(1)
    elif only_marginal:
        all_features = [f for f in all_features if f.quality_label == "MARGINAL"]
        print(f"  -> Filtered to {len(all_features)} MARGINAL sessions")

    print("\n[Phase 1] Training classifier and predicting...")
    classifier = WeldClassifier()
    all_for_training = generate_feature_dataset()
    train_report = classifier.train(all_for_training)
    acc = train_report["train_accuracy"]
    top_3 = train_report["top_3_drivers"]
    print(f"  -> Train accuracy: {acc:.2f}")
    if train_report.get("warning"):
        warn = train_report["warning"]
        print(f"  WARNING: {warn}")
    print(f"  -> Top drivers: {top_3}")

    predictions = {}
    for feat in all_features:
        pred = classifier.predict(feat)
        predictions[feat.session_id] = pred

    print("\n[Phase 2] Initialising WarpSenseAgent...")
    agent = WarpSenseAgent(verbose=verbose_agent)

    reports = []
    total = len(all_features)

    for i, feat in enumerate(all_features, 1):
        pred = predictions[feat.session_id]
        sep = "-" * 58
        print(f"\n{sep}")
        print(f"[{i}/{total}] Session: {feat.session_id} | Label: {feat.quality_label} | Predicted: {pred.quality_class} ({pred.confidence:.2f})")
        print(sep)
        t0 = time.time()
        report = agent.assess(pred, feat)
        elapsed = time.time() - t0
        print(f"\n{report.render()}")
        print(f"[Timing] {elapsed:.2f}s")
        reports.append(report)

    print("\n" + "=" * 58)
    print("PIPELINE SUMMARY")
    print("=" * 58)
    h1, h2, h3, h4, h5 = "Session", "Label", "Predicted", "Disposition", "Conf"
    print(f"{h1:<18} {h2:<12} {h3:<12} {h4:<20} {h5:<6}")
    print("-" * 68)
    for feat, report in zip(all_features, reports):
        match = "OK" if feat.quality_label == report.quality_class else "MISMATCH"
        print(f"{feat.session_id:<18} {feat.quality_label:<12} {match} {report.quality_class:<10} {report.disposition:<20} {report.confidence:.2f}")

    rework = sum(1 for r in reports if r.disposition == "REWORK_REQUIRED")
    cond = sum(1 for r in reports if r.disposition == "CONDITIONAL")
    passed = sum(1 for r in reports if r.disposition == "PASS")
    sc_fails = sum(1 for r in reports if not r.self_check_passed)
    print("-" * 68)
    print(f"PASS: {passed}  |  CONDITIONAL: {cond}  |  REWORK: {rework}")
    print(f"Self-check failures: {sc_fails}/{len(reports)}")
    print("=" * 58)
    return reports


def main():
    parser = argparse.ArgumentParser(description="WarpSense end-to-end runner")
    parser.add_argument("--session", "-s", nargs="+")
    parser.add_argument("--worst", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--rebuild-kb", action="store_true")
    parser.add_argument("--no-build-kb", action="store_true")
    args = parser.parse_args()

    if not args.no_build_kb:
        ensure_kb_exists(force_rebuild=args.rebuild_kb)

    try:
        run_pipeline(
            session_ids=args.session,
            only_marginal=args.worst,
            verbose_agent=not args.quiet,
        )
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
  
