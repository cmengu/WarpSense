"""
eval_multi_agent.py
-------------------
Three-way comparison: single agent vs LangGraph vs LangChain.
Runs all three against the same 24 eval scenarios from Phase 3.

Does NOT modify the Phase 3 evaluator (Open/Closed principle).
The single-agent FNR=0.000 baseline from Phase 3 is the floor.

Note: LangChain agent reports primary_defect_categories=[] (hardcoded).
Metrics that use defect categories will show LangChain performing worse
than actual. FNR/F1 comparison is unaffected.

Usage:
    python eval_multi_agent.py                     # all 24 scenarios, 1 run
    python eval_multi_agent.py --category FN_RISK  # safety gate only
    python eval_multi_agent.py --category FP_RISK  # false-positive gate
    python eval_multi_agent.py --llm-runs 3        # 3 runs per scenario
    python eval_multi_agent.py --save
"""

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional
import logging
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")
from backend.observability.logging_config import configure_logging
configure_logging()

import chromadb

from backend.features.session_feature_extractor import generate_feature_dataset
from backend.features.weld_classifier import WeldClassifier
from backend.agent.warpsense_agent import WarpSenseAgent
from backend.agent.warpsense_graph import WarpSenseGraph
from backend.agent.warpsense_langchain_agent import WarpSenseLangChainAgent
from backend.eval.eval_scenarios import SCENARIOS, EvalScenario, get_scenarios_by_category

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


@dataclass
class AgentEvalResult:
    agent_name:          str
    n_scenarios:         int
    llm_runs:            int
    tp: int
    fp: int
    tn: int
    fn: int
    precision:           float
    recall:              float
    f1:                  float
    fpr:                 float
    fnr:                 float
    mean_fallback_rate:  float
    p50_ms:              float
    p95_ms:              float
    error_count:         int
    scenario_results:    list


@dataclass
class ComparisonReport:
    timestamp:           str
    n_scenarios:         int
    llm_runs:            int
    results:             list[AgentEvalResult]
    winner:              str
    winner_rationale:    str


class MultiAgentEvaluator:
    def __init__(self, llm_runs: int = 1, verbose: bool = True):
        self.llm_runs = llm_runs
        self.verbose = verbose

        self._log("[MultiEval] Training classifier...")
        dataset = generate_feature_dataset()
        self.classifier = WeldClassifier()
        self.classifier.train(dataset)
        self._log(f"[MultiEval] Classifier trained on {len(dataset)} sessions")

        self._log("[MultiEval] Initialising agents...")
        kb_path = Path(__file__).resolve().parent.parent / "knowledge" / "chroma_db"
        shared_client = chromadb.PersistentClient(path=str(kb_path))

        self.agents: dict = {
            "single_agent": WarpSenseAgent(verbose=False),
            "langgraph":    WarpSenseGraph(chroma_client=shared_client, verbose=False),
            "langchain":    WarpSenseLangChainAgent(chroma_client=shared_client, verbose=False),
        }
        self._log("[MultiEval] All 3 agents ready")

    def _log(self, msg: str) -> None:
        if self.verbose:
            logger.info(msg)

    def _detect_fallback(self, report) -> bool:
        fallback_used = False
        if hasattr(report, "root_cause"):
            fallback_used = (
                report.root_cause.startswith("LLM") or
                report.root_cause.startswith("LangChain agent failed") or
                "LLM call failed:" in report.root_cause
            )
        # LangGraph: llm_raw_response is JSON array of SpecialistResult (from SummaryAgent.synthesise)
        if hasattr(report, "llm_raw_response") and report.llm_raw_response:
            try:
                raw_list = json.loads(report.llm_raw_response)
                if isinstance(raw_list, list):
                    fallback_used = fallback_used or any(
                        r.get("fallback_used") for r in raw_list if isinstance(r, dict)
                    )
            except (json.JSONDecodeError, TypeError):
                pass
        return fallback_used

    def _run_once(self, agent, scenario: EvalScenario) -> dict:
        features = scenario.features
        t_start = time.perf_counter()
        prediction = self.classifier.predict(features)
        fallback_used = False
        error = None

        try:
            report = agent.assess(prediction, features)
            fallback_used = self._detect_fallback(report)
            actual = report.disposition
        except Exception as e:
            error = str(e)
            actual = "ERROR"
            fallback_used = True

        total_ms = (time.perf_counter() - t_start) * 1000
        correct = (actual == scenario.expected_disposition)

        return {
            "scenario_id":          scenario.scenario_id,
            "category":             scenario.category,
            "expected_disposition": scenario.expected_disposition,
            "actual_disposition":   actual,
            "correct":              correct,
            "fallback_used":        fallback_used,
            "total_ms":             total_ms,
            "error":                error,
        }

    def evaluate_agent(self, agent_name: str, agent, scenarios: list[EvalScenario]) -> AgentEvalResult:
        self._log(f"\n  [{agent_name}] Running {len(scenarios)} scenarios × {self.llm_runs} run(s)...")

        all_runs = []
        all_latencies = []

        for scenario in scenarios:
            runs = [self._run_once(agent, scenario) for _ in range(self.llm_runs)]
            all_runs.extend(runs)

            actuals = [r["actual_disposition"] for r in runs]
            most_common = Counter(actuals).most_common(1)[0][0]
            correct_count = sum(1 for r in runs if r["correct"])
            lat = mean(r["total_ms"] for r in runs)
            all_latencies.append(lat)

            icon = "✅" if most_common == scenario.expected_disposition else "❌"
            self._log(
                f"    {icon} {scenario.scenario_id}: expected={scenario.expected_disposition} "
                f"actual={most_common} ({correct_count}/{self.llm_runs}) {lat:.0f}ms"
            )

        # Per-scenario aggregates using most_common_actual
        scenario_aggs = []
        for scenario in scenarios:
            scenario_runs = [r for r in all_runs if r["scenario_id"] == scenario.scenario_id]
            actuals = [r["actual_disposition"] for r in scenario_runs]
            most_common = Counter(actuals).most_common(1)[0][0]
            scenario_aggs.append({
                "scenario_id":          scenario.scenario_id,
                "category":             scenario.category,
                "expected_disposition": scenario.expected_disposition,
                "most_common_actual":   most_common,
                "correct_rate":         sum(1 for r in scenario_runs if r["correct"]) / len(scenario_runs),
            })

        # Confusion matrix from most_common_actual
        tp = fp = tn = fn = error_count = 0
        for agg in scenario_aggs:
            exp = agg["expected_disposition"]
            act = agg["most_common_actual"]
            if act == "ERROR":
                error_count += 1
            if exp == "REWORK_REQUIRED" and act == "REWORK_REQUIRED":
                tp += 1
            elif exp != "REWORK_REQUIRED" and act == "REWORK_REQUIRED":
                fp += 1
            elif exp != "REWORK_REQUIRED" and act not in ("REWORK_REQUIRED", "ERROR"):
                tn += 1
            elif exp == "REWORK_REQUIRED" and act != "REWORK_REQUIRED":
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        fallback_rate = mean(1.0 if r["fallback_used"] else 0.0 for r in all_runs)

        sorted_lat = sorted(all_latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[min(int(n * 0.95), n - 1)]

        fnr_note = " ✅ HEADLINE" if fnr == 0.0 else " ⚠️ SAFETY MISS"
        self._log(f"\n  [{agent_name}] F1={f1:.3f} FNR={fnr:.3f}{fnr_note} p95={p95:.0f}ms errors={error_count}")

        return AgentEvalResult(
            agent_name=agent_name, n_scenarios=len(scenarios), llm_runs=self.llm_runs,
            tp=tp, fp=fp, tn=tn, fn=fn,
            precision=precision, recall=recall, f1=f1, fpr=fpr, fnr=fnr,
            mean_fallback_rate=fallback_rate, p50_ms=p50, p95_ms=p95,
            error_count=error_count, scenario_results=scenario_aggs,
        )

    def evaluate_all(self, scenarios: list[EvalScenario]) -> ComparisonReport:
        self._log(f"\n{'='*65}")
        self._log(f"WARPSENSE MULTI-AGENT EVAL — {len(scenarios)} scenarios × {self.llm_runs} run(s)")
        self._log(f"{'='*65}")

        results = []
        for agent_name, agent in self.agents.items():
            result = self.evaluate_agent(agent_name, agent, scenarios)
            results.append(result)

        qualified = [r for r in results if r.fnr == 0.0]
        if not qualified:
            winner = min(results, key=lambda r: r.fnr)
            winner_rationale = f"No agent achieved FNR=0.000. Lowest FNR: {winner.agent_name} ({winner.fnr:.3f})"
        else:
            winner = max(qualified, key=lambda r: (r.f1, -r.p95_ms))
            winner_rationale = f"{winner.agent_name} achieves FNR=0.000 with F1={winner.f1:.3f} and p95={winner.p95_ms:.0f}ms."

        report = ComparisonReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            n_scenarios=len(scenarios), llm_runs=self.llm_runs,
            results=results, winner=winner.agent_name, winner_rationale=winner_rationale,
        )
        self._print_comparison_table(report)
        return report

    def _print_comparison_table(self, report: ComparisonReport) -> None:
        w = 75
        print(f"\n{'='*w}")
        print("WARPSENSE MULTI-AGENT COMPARISON")
        print(f"{'='*w}")

        names = [r.agent_name for r in report.results]
        col_w = 16
        print(f"\n  {'Metric':<28} " + "".join(f"{n:<{col_w}}" for n in names))
        print(f"  {'-'*70}")

        def row(label, values):
            print(f"  {label:<28} " + "".join(f"{str(v):<{col_w}}" for v in values))

        row("F1",              [f"{r.f1:.3f}"      for r in report.results])
        row("FNR (safety) ←", [f"{r.fnr:.3f}{'✅' if r.fnr==0 else '⚠️'}" for r in report.results])
        row("Precision",       [f"{r.precision:.3f}" for r in report.results])
        row("Recall",          [f"{r.recall:.3f}"  for r in report.results])
        row("FPR",             [f"{r.fpr:.3f}"     for r in report.results])
        row("Fallback rate",   [f"{r.mean_fallback_rate:.1%}" for r in report.results])
        row("Error count",     [str(r.error_count) for r in report.results])
        row("p50 latency (ms)",[f"{r.p50_ms:.0f}"  for r in report.results])
        row("p95 latency (ms)",[f"{r.p95_ms:.0f}"  for r in report.results])

        print(f"\n  FNR=0.000 is the safety gate. Any agent above 0.000 is not production-ready.")
        print(f"  Note: LangChain primary_defect_categories=[] (hardcoded) — defect category metrics affected.")
        print(f"\n  Winner: {report.winner}")
        print(f"  {report.winner_rationale}")

        fn_failures = {}
        for r in report.results:
            fn_fails = [s for s in r.scenario_results
                        if s["category"] == "FN_RISK" and s["most_common_actual"] != "REWORK_REQUIRED"]
            if fn_fails:
                fn_failures[r.agent_name] = fn_fails
        if fn_failures:
            print(f"\n  ⚠️  FALSE-NEGATIVE FAILURES:")
            for agent_name, fails in fn_failures.items():
                for f in fails:
                    print(f"     {agent_name}: {f['scenario_id']} → {f['most_common_actual']}")
        else:
            print(f"\n  ✅ All agents passed FNR gate on safety-critical scenarios.")

        print(f"\n{'='*w}\n")

    def save(self, report: ComparisonReport) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"multi_agent_eval_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        print(f"[MultiEval] Results saved: {out}")
        return out


def main():
    parser = argparse.ArgumentParser(description="WarpSense multi-agent comparison evaluator")
    parser.add_argument("--llm-runs", type=int, default=1)
    parser.add_argument("--category", type=str, default=None,
                        choices=["TRUE_REWORK", "TRUE_PASS", "FP_RISK", "FN_RISK"])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    if args.llm_runs < 1:
        parser.error("--llm-runs must be >= 1")

    scenarios = get_scenarios_by_category(args.category) if args.category else SCENARIOS

    evaluator = MultiAgentEvaluator(llm_runs=args.llm_runs, verbose=not args.quiet)
    report = evaluator.evaluate_all(scenarios)

    if args.save:
        evaluator.save(report)

    error_exit = False
    for r in report.results:
        if r.error_count > 0:
            print(f"WARN: {r.agent_name} had {r.error_count} ERROR result(s) — check agent logs")
        fn_fails = [s for s in r.scenario_results
                    if s["category"] == "FN_RISK" and s["most_common_actual"] != "REWORK_REQUIRED"]
        if fn_fails:
            print(f"FAIL: {r.agent_name} missed {len(fn_fails)} FN_RISK scenario(s) — not production-ready")
            error_exit = True
        fp_fails = [s for s in r.scenario_results
                    if s["category"] == "FP_RISK" and s["most_common_actual"] == "REWORK_REQUIRED"]
        if fp_fails:
            print(f"FAIL: {r.agent_name} false-positive on {len(fp_fails)} FP_RISK scenario(s)")
            error_exit = True

    if error_exit:
        sys.exit(1)


if __name__ == "__main__":
    main()
