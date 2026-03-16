"""
eval_pipeline.py
----------------
Runs all 24 eval scenarios against the WarpSense pipeline.
Computes F1, FNR, Precision, Recall, FPR, and latency.
LLM metrics run each scenario N times and report mean.

Usage:
    python eval_pipeline.py                     # all 24 scenarios, 1 run each
    python eval_pipeline.py --llm-runs 3        # LLM metrics: run each 3 times
    python eval_pipeline.py --category FN_RISK  # run only false-negative cases
    python eval_pipeline.py --save              # write results to JSON
"""

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from backend.agent.warpsense_agent import WarpSenseAgent
from backend.eval.eval_scenarios import SCENARIOS, EvalScenario, get_scenarios_by_category
from backend.features.session_feature_extractor import generate_feature_dataset
from backend.features.weld_classifier import WeldClassifier

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


@dataclass
class ScenarioRunResult:
    scenario_id: str
    category: str
    expected_disposition: str
    actual_disposition: str
    correct: bool
    iso_5817_level: str
    confidence: float
    self_check_passed: bool
    fallback_used: bool
    total_ms: float
    error: Optional[str] = None


@dataclass
class ScenarioAggregateResult:
    scenario_id: str
    category: str
    expected_disposition: str
    runs: int
    correct_count: int
    disposition_match_rate: float
    most_common_actual: str
    llm_response_rate: float
    fallback_rate: float
    self_check_pass_rate: float
    mean_total_ms: float
    std_total_ms: float


@dataclass
class PipelineEvalReport:
    timestamp: str
    n_scenarios: int
    llm_runs_per_scenario: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    fpr: float
    fnr: float
    mean_llm_response_rate: float
    mean_fallback_rate: float
    mean_self_check_pass: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    scenario_results: list


class PipelineEvaluator:
    def __init__(self, llm_runs: int = 1, verbose: bool = True):
        self.llm_runs = llm_runs
        self.verbose = verbose

        self._log("[Eval] Training classifier...")
        dataset = generate_feature_dataset()
        self.classifier = WeldClassifier()
        self.classifier.train(dataset)
        self._log(f"[Eval] Classifier trained on {len(dataset)} sessions")

        self._log("[Eval] Initialising WarpSenseAgent...")
        self.agent = WarpSenseAgent(verbose=False)
        self._log("[Eval] Agent ready")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _run_single(self, scenario: EvalScenario) -> ScenarioRunResult:
        features = scenario.features

        t_start = time.perf_counter()
        prediction = self.classifier.predict(features)

        fallback_used = False
        error = None
        try:
            report = self.agent.assess(prediction, features)
            fallback_used = "LLM generation failed" in report.root_cause
        except Exception as e:
            error = str(e)
            report = None

        total_ms = (time.perf_counter() - t_start) * 1000

        if report is None:
            return ScenarioRunResult(
                scenario_id=scenario.scenario_id,
                category=scenario.category,
                expected_disposition=scenario.expected_disposition,
                actual_disposition="ERROR",
                correct=False,
                iso_5817_level="ERROR",
                confidence=0.0,
                self_check_passed=False,
                fallback_used=True,
                total_ms=total_ms,
                error=error,
            )

        actual = report.disposition
        return ScenarioRunResult(
            scenario_id=scenario.scenario_id,
            category=scenario.category,
            expected_disposition=scenario.expected_disposition,
            actual_disposition=actual,
            correct=(actual == scenario.expected_disposition),
            iso_5817_level=report.iso_5817_level,
            confidence=report.confidence,
            self_check_passed=report.self_check_passed,
            fallback_used=fallback_used,
            total_ms=total_ms,
            error=error,
        )

    def _run_scenario_aggregate(self, scenario: EvalScenario) -> ScenarioAggregateResult:
        runs = [self._run_single(scenario) for _ in range(self.llm_runs)]
        n = len(runs)
        latencies = [r.total_ms for r in runs]
        actual_dispositions = [r.actual_disposition for r in runs]

        correct_count = sum(1 for r in runs if r.correct)
        llm_responded = sum(1 for r in runs if r.iso_5817_level not in ("", "ERROR"))
        fallback_count = sum(1 for r in runs if r.fallback_used)
        sc_pass_count = sum(1 for r in runs if r.self_check_passed)
        most_common_actual = Counter(actual_dispositions).most_common(1)[0][0]

        return ScenarioAggregateResult(
            scenario_id=scenario.scenario_id,
            category=scenario.category,
            expected_disposition=scenario.expected_disposition,
            runs=n,
            correct_count=correct_count,
            disposition_match_rate=correct_count / n,
            most_common_actual=most_common_actual,
            llm_response_rate=llm_responded / n,
            fallback_rate=fallback_count / n,
            self_check_pass_rate=sc_pass_count / n,
            mean_total_ms=mean(latencies),
            std_total_ms=stdev(latencies) if n > 1 else 0.0,
        )

    def evaluate(self, scenarios: list[EvalScenario]) -> PipelineEvalReport:
        self._log(f"\n{'=' * 60}")
        self._log(
            f"WARPSENSE PIPELINE EVAL — {len(scenarios)} scenarios × {self.llm_runs} run(s)"
        )
        self._log(f"{'=' * 60}\n")

        agg_results = []
        all_latencies = []
        for idx, scenario in enumerate(scenarios, 1):
            self._log(f"[{idx:02d}/{len(scenarios)}] {scenario.scenario_id} ({scenario.category})")
            agg = self._run_scenario_aggregate(scenario)
            agg_results.append(agg)
            all_latencies.append(agg.mean_total_ms)
            icon = "✅" if agg.disposition_match_rate == 1.0 else "❌"
            self._log(
                f"        {icon} match={agg.disposition_match_rate:.0%} "
                f"expected={agg.expected_disposition} actual={agg.most_common_actual} "
                f"latency={agg.mean_total_ms:.0f}ms"
            )

        tp = fp = tn = fn = 0
        for agg in agg_results:
            expected = agg.expected_disposition
            actual = agg.most_common_actual
            if expected == "REWORK_REQUIRED" and actual == "REWORK_REQUIRED":
                tp += 1
            elif expected != "REWORK_REQUIRED" and actual == "REWORK_REQUIRED":
                fp += 1
            elif expected != "REWORK_REQUIRED" and actual != "REWORK_REQUIRED":
                tn += 1
            elif expected == "REWORK_REQUIRED" and actual != "REWORK_REQUIRED":
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        mean_llm_resp = mean(a.llm_response_rate for a in agg_results)
        mean_fallback = mean(a.fallback_rate for a in agg_results)
        mean_sc_pass = mean(a.self_check_pass_rate for a in agg_results)

        sorted_lat = sorted(all_latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[min(int(n * 0.95), n - 1)]
        p99 = sorted_lat[min(int(n * 0.99), n - 1)]

        report = PipelineEvalReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            n_scenarios=len(scenarios),
            llm_runs_per_scenario=self.llm_runs,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            fpr=fpr,
            fnr=fnr,
            mean_llm_response_rate=mean_llm_resp,
            mean_fallback_rate=mean_fallback,
            mean_self_check_pass=mean_sc_pass,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            scenario_results=[asdict(a) for a in agg_results],
        )
        self._print_summary(report, agg_results)
        return report

    def _print_summary(
        self, report: PipelineEvalReport, agg_results: list[ScenarioAggregateResult]
    ) -> None:
        w = 60
        print(f"\n{'=' * w}")
        print("PIPELINE EVAL SUMMARY")
        print(f"{'=' * w}")
        print("\nClassification Metrics (positive = REWORK_REQUIRED):")
        print(f"  {'Metric':<25} {'Score'}")
        print(f"  {'-' * 35}")
        print(f"  {'Precision':<25} {report.precision:.3f}")
        print(f"  {'Recall':<25} {report.recall:.3f}")
        print(f"  {'F1':<25} {report.f1:.3f}")
        print(f"  {'FPR (false alarm rate)':<25} {report.fpr:.3f}")
        fnr_note = " ← HEADLINE (safety)" if report.fnr == 0.0 else " ← WARNING: misses"
        print(f"  {'FNR (missed defects)':<25} {report.fnr:.3f}{fnr_note}")
        print(
            f"  {'TP / FP / TN / FN':<25} {report.tp} / {report.fp} / {report.tn} / {report.fn}"
        )

        print(f"\nLLM Metrics (mean over {report.llm_runs_per_scenario} run(s)):")
        print(
            f"  {'LLM response rate':<30} {report.mean_llm_response_rate:.1%}  "
            "(non-empty iso_5817_level — not true alignment)"
        )
        print(f"  {'Fallback rate':<30} {report.mean_fallback_rate:.1%}")
        print(f"  {'Self-check pass rate':<30} {report.mean_self_check_pass:.1%}")

        print("\nLatency (ms):")
        print(f"  {'p50':<30} {report.p50_ms:.0f} ms")
        print(f"  {'p95':<30} {report.p95_ms:.0f} ms")
        print(f"  {'p99':<30} {report.p99_ms:.0f} ms")
        print("  Component breakdown: Phase 6 (RunTracer)")

        failures = [a for a in agg_results if a.disposition_match_rate < 1.0]
        fn_failures = [
            a for a in agg_results if a.category == "FN_RISK" and a.disposition_match_rate < 1.0
        ]
        if fn_failures:
            print(f"\n⚠️  CRITICAL: {len(fn_failures)} FALSE-NEGATIVE failures:")
            for item in fn_failures:
                print(
                    f"   {item.scenario_id} — expected REWORK_REQUIRED, got {item.most_common_actual}"
                )
        elif failures:
            print(f"\n⚠️  {len(failures)} scenario(s) failed (non-safety-critical)")
        else:
            print(f"\n✅ All {len(agg_results)} scenarios passed")
        print(f"{'=' * w}\n")

    def save(self, report: PipelineEvalReport) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"pipeline_eval_{ts}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        print(f"[Eval] Results saved: {out}")
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description="WarpSense pipeline evaluator")
    parser.add_argument("--llm-runs", type=int, default=1)
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["TRUE_REWORK", "TRUE_PASS", "FP_RISK", "FN_RISK"],
    )
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    if args.llm_runs < 1:
        parser.error("--llm-runs must be >= 1")

    if args.scenario:
        scenarios = [s for s in SCENARIOS if s.scenario_id == args.scenario]
        if not scenarios:
            print(f"ERROR: scenario '{args.scenario}' not found")
            sys.exit(1)
    elif args.category:
        scenarios = get_scenarios_by_category(args.category)
    else:
        scenarios = SCENARIOS

    evaluator = PipelineEvaluator(llm_runs=args.llm_runs, verbose=not args.quiet)
    report = evaluator.evaluate(scenarios)

    if args.save:
        evaluator.save(report)

    error_runs = [
        r
        for r in report.scenario_results
        if r.get("most_common_actual") == "ERROR" or r.get("actual_disposition") == "ERROR"
    ]
    if error_runs:
        print(f"FAIL: {len(error_runs)} scenario(s) returned ERROR — evaluation run is invalid")
        sys.exit(1)

    fn_failures = [
        r
        for r in report.scenario_results
        if r["category"] == "FN_RISK" and r["disposition_match_rate"] < 1.0
    ]
    if fn_failures:
        print(f"FAIL: {len(fn_failures)} FN_RISK scenario(s) failed — safety-critical")
        sys.exit(1)


if __name__ == "__main__":
    main()
