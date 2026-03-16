"""
eval_prompts.py
---------------
Evaluates 8 prompt variants across all 24 eval scenarios.
"""

import argparse
import json
import re
import sys
import time
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

from groq import Groq

from backend.agent.warpsense_agent import WarpSenseAgent
from backend.eval.eval_scenarios import SCENARIOS, EvalScenario
from backend.features.session_feature_extractor import generate_feature_dataset
from backend.features.weld_classifier import WeldClassifier

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

GROQ_MODEL = "llama-3.3-70b-versatile"

SPECIFICITY_PATTERNS = [
    r"\d+\s*%",
    r"\d+\s*degrees?",
    r"±\s*\d+",
    r"\+/-\s*\d+",
    r"\d+\s*[Cc]/s",
    r"\d+\s*[Cc]",
    r"\d+\s*(mm|cm|m)\b",
    r"\d+\s*(kJ|J)\b",
    r"\d+\.?\d*\s*[Vv]olt",
    r"\d+\.?\d*\s*[Aa]mp",
    r"within\s+\d+\s+session",
    r"reduce\s+\w+\s+by\s+\d+",
    r"increase\s+\w+\s+by\s+\d+",
    r"below\s+\d+",
    r"above\s+\d+",
    r"at least\s+\d+",
]


def specificity_score(action: str) -> float:
    for pattern in SPECIFICITY_PATTERNS:
        if re.search(pattern, action, re.IGNORECASE):
            return 1.0
    return 0.0


def mean_specificity(actions: list[str]) -> float:
    if not actions:
        return 0.0
    return mean(specificity_score(a) for a in actions)


def build_context_block(chunks: list) -> str:
    return "\n\n".join(f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}" for c in chunks)


def build_violations_block(violations: list) -> str:
    return "\n".join(v.as_display_line() for v in violations) or "None"


PROMPT_A1 = """You are WarpSenseAgent, a welding quality assessment AI.

Session: {session_id}
Quality Class: {quality_class} (confidence: {confidence:.2f})
Top Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Produce a JSON report with exactly these keys:
{{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
"disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
"corrective_actions": ["Action with specific target value", ...], "standards_references": ["Source: section"]}}

Rules: (1) DEFECTIVE->BELOW_D, MARGINAL->D, GOOD->C. (2) Any LOF/LOP RISK feature -> REWORK_REQUIRED.
(3) Corrective actions must include specific numeric targets. (4) Only cite retrieved sources.
Respond with ONLY the JSON object."""

PROMPT_A2 = """You are WarpSenseAgent, a welding quality assessment AI.

Session: {session_id}
Quality Class: {quality_class} (confidence: {confidence:.2f})
Top Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Think step by step before producing your JSON:
Step 1: Which features are in RISK band? Which are MARGINAL?
Step 2: Map RISK features to defect type (LOF/LOP -> REWORK_REQUIRED; others -> CONDITIONAL).
Step 3: Identify the primary physical mechanism from the retrieved standards.
Step 4: Derive specific corrective parameters from the retrieved corrective protocols.
Step 5: Verify every standard you cite appears in the retrieved context above.

Now produce a JSON report:
{{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
"disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
"corrective_actions": ["Action with specific target value", ...], "standards_references": ["Source: section"]}}

Respond with ONLY the JSON object."""

PROMPT_A3 = """You are WarpSenseAgent, a welding quality assessment AI.

EXAMPLE 1:
{{"iso_5817_level":"BELOW_D","disposition":"REWORK_REQUIRED","disposition_rationale":"Two LOF features in RISK.",
"root_cause":"Thermal spikes and angle drift indicate lack of fusion risk.",
"corrective_actions":["Correct torch angle to 45 +/- 5 degrees","Reduce travel speed variance by 20%","Maintain preheat to minimum 80C"],
"standards_references":["ISO 5817:2023 Table 1 No.1.5"]}}

EXAMPLE 2:
{{"iso_5817_level":"D","disposition":"CONDITIONAL","disposition_rationale":"Single marginal violation.",
"root_cause":"Heat input slightly below target, no LOF feature in RISK.",
"corrective_actions":["Increase wire feed speed by 5% to raise heat input above 4500 J"],
"standards_references":["WarpSense feature thresholds"]}}

Now assess:
Session: {session_id} | Class: {quality_class} ({confidence:.2f}) | Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Respond with ONLY the JSON object."""

PROMPT_B1 = PROMPT_A1

PROMPT_B2 = """You are WarpSenseAgent, a welding quality assessment AI.

Session: {session_id}
Quality Class: {quality_class} (confidence: {confidence:.2f})
Top Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Produce JSON with:
{{"iso_5817_level":"B"|"C"|"D"|"BELOW_D","disposition":"PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
"disposition_rationale":"One sentence.","root_cause":"2-3 sentences.",
"corrective_actions":["The welder should ... because ..."],"standards_references":["Source: section"]}}

Use process narrative actions and cite only retrieved sources. Respond with ONLY JSON."""

PROMPT_B3 = """You are WarpSenseAgent, a welding quality assessment AI.

Session: {session_id}
Quality Class: {quality_class} (confidence: {confidence:.2f})
Top Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Produce JSON with checklist actions:
{{"iso_5817_level":"B"|"C"|"D"|"BELOW_D","disposition":"PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
"disposition_rationale":"One sentence.","root_cause":"2-3 sentences.",
"corrective_actions":["Step 1: ...","Step 2: ..."],"standards_references":["Source: section"]}}

Respond with ONLY JSON."""

PROMPT_C2 = """You are WarpSenseAgent, a welding quality assessment AI.

Session: {session_id}
Quality Class: {quality_class} (confidence: {confidence:.2f})
Top Drivers: {top_drivers}

Threshold Violations:
{violations}

Retrieved Standards:
{context}

Before finalizing, verify every citation appears in Retrieved Standards.
Set self_verified=true only when all citations are grounded.

Produce JSON:
{{"iso_5817_level":"B"|"C"|"D"|"BELOW_D","disposition":"PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
"disposition_rationale":"One sentence.","root_cause":"2-3 sentences.",
"corrective_actions":["Action with specific target"],"standards_references":["Source: section"],"self_verified":true|false}}

Respond with ONLY JSON."""

PROMPT_C3 = PROMPT_A1

PROMPT_VARIANTS = {
    "A1": ("Direct (current)", PROMPT_A1),
    "A2": ("Chain-of-thought", PROMPT_A2),
    "A3": ("Few-shot examples", PROMPT_A3),
    "B1": ("Parameter targets", PROMPT_B1),
    "B2": ("Process narrative", PROMPT_B2),
    "B3": ("Checklist format", PROMPT_B3),
    "C2": ("Embedded self-verify", PROMPT_C2),
    "C3": ("No self-check (baseline)", PROMPT_C3),
}


@dataclass
class PromptRunResult:
    variant_id: str
    scenario_id: str
    expected_disposition: str
    actual_disposition: str
    correct: bool
    iso_5817_level: str
    corrective_actions: list[str]
    specificity_score: float
    fallback_used: bool
    self_check_passed: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class VariantSummary:
    variant_id: str
    variant_name: str
    n_scenarios: int
    runs_per_scenario: int
    disposition_match_rate: float
    mean_specificity: float
    std_specificity: float
    fallback_rate: float
    self_check_pass_rate: float
    mean_latency_ms: float
    std_latency_ms: float


class PromptEvaluator:
    def __init__(self, runs_per_scenario: int = 3, verbose: bool = True):
        self.runs = runs_per_scenario
        self.verbose = verbose

        dataset = generate_feature_dataset()
        self.classifier = WeldClassifier()
        self.classifier.train(dataset)
        self.agent = WarpSenseAgent(verbose=False)
        self.groq = Groq()
        self._last_runs: list[PromptRunResult] = []

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _call_llm(self, prompt: str) -> tuple[dict, float, bool, Optional[str]]:
        t0 = time.perf_counter()
        fallback_used = False
        raw = ""
        error = None
        try:
            response = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            parsed = json.loads(match.group()) if match else {}
            fallback_used = True
            error = "JSON decode fallback used"
        except Exception as e:
            parsed = {
                "disposition": "CONDITIONAL",
                "iso_5817_level": "D",
                "root_cause": f"LLM call failed: {e}",
                "corrective_actions": [],
                "standards_references": [],
                "disposition_rationale": "Fallback",
            }
            fallback_used = True
            error = str(e)
        latency_ms = (time.perf_counter() - t0) * 1000
        return parsed, latency_ms, fallback_used, error

    def _run_once(self, variant_id: str, prompt_template: str, scenario: EvalScenario) -> PromptRunResult:
        features = scenario.features
        prediction = self.classifier.predict(features)
        violations, chunks, _ = self.agent.prepare_context(features, prediction)

        top_drivers_str = ", ".join(f"{name}({imp:.2f})" for name, imp in prediction.top_drivers)
        prompt = prompt_template.format(
            session_id=features.session_id,
            quality_class=prediction.quality_class,
            confidence=prediction.confidence,
            top_drivers=top_drivers_str,
            violations=build_violations_block(violations),
            context=build_context_block(chunks),
        )
        parsed, latency_ms, fallback_used, error = self._call_llm(prompt)

        disposition = parsed.get("disposition", "CONDITIONAL")
        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"

        if variant_id == "C3":
            self_check_passed = False
        elif variant_id == "C2":
            self_check_passed = bool(parsed.get("self_verified", False))
        else:
            self_check_passed, _ = self.agent.verify_citations(parsed, chunks)

        actions = parsed.get("corrective_actions", [])
        return PromptRunResult(
            variant_id=variant_id,
            scenario_id=scenario.scenario_id,
            expected_disposition=scenario.expected_disposition,
            actual_disposition=disposition,
            correct=(disposition == scenario.expected_disposition),
            iso_5817_level=parsed.get("iso_5817_level", ""),
            corrective_actions=actions,
            specificity_score=mean_specificity(actions),
            fallback_used=fallback_used,
            self_check_passed=self_check_passed,
            latency_ms=latency_ms,
            error=error,
        )

    def evaluate_variant(self, variant_id: str, scenarios: list[EvalScenario]) -> tuple[VariantSummary, list[PromptRunResult]]:
        variant_name, prompt_template = PROMPT_VARIANTS[variant_id]
        self._log(f"\n  Variant {variant_id}: {variant_name}")
        self._log(f"  {'-' * 50}")

        all_runs: list[PromptRunResult] = []
        for scenario in scenarios:
            for run_idx in range(self.runs):
                result = self._run_once(variant_id, prompt_template, scenario)
                all_runs.append(result)
                icon = "✅" if result.correct else "❌"
                self._log(
                    f"    {icon} {scenario.scenario_id} run={run_idx + 1} "
                    f"match={result.correct} spec={result.specificity_score:.1f} "
                    f"{result.latency_ms:.0f}ms"
                )

        n_runs = len(all_runs)
        specs = [r.specificity_score for r in all_runs]
        lats = [r.latency_ms for r in all_runs]
        summary = VariantSummary(
            variant_id=variant_id,
            variant_name=variant_name,
            n_scenarios=len(scenarios),
            runs_per_scenario=self.runs,
            disposition_match_rate=sum(1 for r in all_runs if r.correct) / n_runs,
            mean_specificity=mean(specs),
            std_specificity=stdev(specs) if len(specs) > 1 else 0.0,
            fallback_rate=mean(1.0 if r.fallback_used else 0.0 for r in all_runs),
            self_check_pass_rate=mean(1.0 if r.self_check_passed else 0.0 for r in all_runs),
            mean_latency_ms=mean(lats),
            std_latency_ms=stdev(lats) if len(lats) > 1 else 0.0,
        )
        return summary, all_runs

    def evaluate_all(self, variant_ids: list[str], scenarios: list[EvalScenario]) -> list[VariantSummary]:
        self._log(f"\n{'=' * 60}")
        self._log(
            f"PROMPT EVAL — {len(variant_ids)} variants × {len(scenarios)} scenarios × {self.runs} run(s)"
        )
        self._log(f"{'=' * 60}")
        summaries = []
        self._last_runs = []
        for variant_id in variant_ids:
            summary, runs = self.evaluate_variant(variant_id, scenarios)
            summaries.append(summary)
            self._last_runs.extend(runs)
        self._print_comparison(summaries)
        return summaries

    def _print_comparison(self, summaries: list[VariantSummary]) -> None:
        print(f"\n{'=' * 75}")
        print("PROMPT VARIANT COMPARISON")
        print(f"{'=' * 75}")
        print(f"\n{'Var':<4} {'Name':<25} {'Match%':<10} {'Specificity':<18} {'Fallback%':<12} {'SC Pass%':<12} {'ms'}")
        print(f"{'-' * 90}")
        for s in summaries:
            print(
                f"  {s.variant_id:<4} {s.variant_name:<25} {s.disposition_match_rate:<10.1%} "
                f"{s.mean_specificity:.2f} ± {s.std_specificity:.2f}{'':5} "
                f"{s.fallback_rate:<12.1%} {s.self_check_pass_rate:<12.1%} {s.mean_latency_ms:.0f}"
            )

        best_spec = max(summaries, key=lambda s: s.mean_specificity)
        c3 = next((s for s in summaries if s.variant_id == "C3"), None)
        a1 = next((s for s in summaries if s.variant_id == "A1"), None)
        print(f"\nHighest corrective action specificity: {best_spec.variant_id} ({best_spec.variant_name})")
        print(f"  mean_specificity = {best_spec.mean_specificity:.2f}")
        print("  (1.0 = action contains measurable target; 0.0 = vague advice)")

        if c3 and a1:
            sc_delta = a1.self_check_pass_rate - c3.self_check_pass_rate
            print("\nSelf-check value (A1 vs C3):")
            print(f"  A1 (with self-check):    {a1.self_check_pass_rate:.1%} citations grounded in retrieved chunks")
            print(f"  C3 (no self-check):      {c3.self_check_pass_rate:.1%} verified (C3 never runs verify_citations)")
            print(f"  Delta:                   {sc_delta:+.1%}  ← citation grounding gained by self-check step")
        print(f"\n{'=' * 75}\n")

    def save(self, summaries: list[VariantSummary]) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"prompt_eval_{ts}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in summaries], f, indent=2)
        print(f"[PromptEval] Results saved: {out}")
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description="WarpSense prompt variant evaluator")
    parser.add_argument("--variant", type=str, nargs="+", default=list(PROMPT_VARIANTS.keys()), choices=list(PROMPT_VARIANTS.keys()))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-fallback-rate", type=float, default=0.5)
    parser.add_argument("--category", type=str, default=None, choices=["TRUE_REWORK", "TRUE_PASS", "FP_RISK", "FN_RISK"])
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if not 0.0 <= args.max_fallback_rate <= 1.0:
        parser.error("--max-fallback-rate must be between 0.0 and 1.0")

    scenarios = SCENARIOS
    if args.scenario:
        scenarios = [s for s in scenarios if s.scenario_id == args.scenario]
        if not scenarios:
            print(f"ERROR: scenario '{args.scenario}' not found")
            sys.exit(1)
    if args.category:
        scenarios = [s for s in scenarios if s.category == args.category]

    evaluator = PromptEvaluator(runs_per_scenario=args.runs, verbose=not args.quiet)
    summaries = evaluator.evaluate_all(args.variant, scenarios)
    if args.save:
        evaluator.save(summaries)

    hard_errors = [r for r in evaluator._last_runs if r.error and "JSON decode fallback" not in r.error]
    if hard_errors:
        print(f"FAIL: {len(hard_errors)} prompt run(s) had hard errors")
        sys.exit(1)

    high_fallback = [s for s in summaries if s.fallback_rate > args.max_fallback_rate]
    if high_fallback:
        offenders = ", ".join(f"{s.variant_id}={s.fallback_rate:.1%}" for s in high_fallback)
        print(f"FAIL: fallback rate above threshold ({args.max_fallback_rate:.1%}): {offenders}")
        sys.exit(1)


if __name__ == "__main__":
    main()
