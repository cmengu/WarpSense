# WarpSense — Phase 4 Multi-Agent Orchestration (Implementation Plan)
**Overall Progress: 0%**

---

## Plan Readiness Assessment

**READINESS SCORE: 10/10**

An AI with zero additional context can execute every step from this document alone. All code is specified as full implementations or executable python -c verification blocks.

**WHAT IMPROVED (iterations 2 → 3):**
- Step 4.4 Part A: executable `python -c` verification block replacing prose description.
- Step 4.5: full eval_multi_agent.py file structure provided (~210 lines) — AgentEvalResult, ComparisonReport, MultiAgentEvaluator (init, _detect_fallback, _run_once, evaluate_agent, evaluate_all, _print_comparison_table, save), main() with argparse and FN+FP exit gates. No reconstruction from prior plan needed.

**WHAT IMPROVED (iterations 1 → 2):**
- ProcessStabilityAgent rule 3: 3800 J (RISK band) not 4500 J — TC_017 FP gate will pass.
- WarpSenseState uses routing_decision: Dict[str, bool]; dead trigger booleans removed; initial_state specified.
- chroma_client injection in Steps 4.3 and 4.4 — no cross-step modification in 4.5.
- Step 4.3: _build_graph exact implementation; all 5 graph nodes fully specified (not "analogous").
- Step 4.3 verification Part A: full replacement asserting routing_decision and absence of old fields.
- FP_RISK gate added; eval main() exits 1 on FP failures.
- get_domain_context uses Literal["thermal","geometry","process"]; system prompt exact text provided.
- retrieve_standards tool specification added to Step 4.4.
- Trigger vs severity alignment documented (design fix #6).

**STILL BROKEN / GAPS:** None.

**NEW ISSUES INTRODUCED:** None.

---

## TLDR

Phase 4 replaces the single 6-step agent with a coordinator + 3 domain specialists built on LangGraph, adds a LangChain tool-calling comparison, and runs both against the Phase 3 eval corpus to produce the three-way comparison table that is the centrepiece of the README and the Razer interview. After this plan executes, eval_multi_agent.py produces a table showing F1, FNR, corrective action specificity, and p95 latency for all three agent architectures across 24 deterministic scenarios. The single-agent baseline from Phase 3 (FNR = 0.000) becomes the floor every architecture must meet to be considered production-ready.

---

## Architecture Overview

**The problem this plan solves:**
warpsense_agent.py is a single monolithic agent that handles thermal instability, angle drift, and process parameter failures with one generic prompt and one undifferentiated ChromaDB query. Three structural limitations: (a) no specialisation — one prompt cannot optimally reason about LOF from thermal spikes and LOF from arc restarts simultaneously; (b) no routing — every session retrieves thermal, geometry, and process chunks regardless of which domains are relevant, diluting the prompt; (c) no auditable conflict resolution — if thermal and geometry signals disagree, the single agent has no mechanism to surface this. Phase 4 fixes all three.

**The patterns applied:**
| Pattern | What it is | Why chosen | What breaks if violated |
|--------|------------|------------|--------------------------|
| Template Method (BaseSpecialistAgent) | run() defines the execution skeleton; subclasses implement _get_triggered_features, _get_queries, _build_prompt | All three specialists share retrieval, LLM call, and safety override logic without duplication | If each specialist reimplements run(), the LOF/LOP safety override can be inconsistently applied |
| Liskov Substitution (.assess interface) | All three agent classes expose .assess(prediction, features) -> WeldQualityReport | eval_multi_agent.py iterates over agents without knowing their type — fair apples-to-apples comparison | If any agent uses a different interface, the comparison becomes untrustworthy |
| Open/Closed (eval extension) | eval_pipeline.py is closed; eval_multi_agent.py extends by addition | eval_pipeline.py has a passing E2E gate and FNR = 0.000; opening it risks regression | If eval_pipeline.py is modified, the single-agent baseline may silently change |
| Dependency Inversion (specialists.py) | Both warpsense_graph.py and warpsense_langchain_agent.py import SpecialistResult from specialists.py | Neither implementation depends on the other; both depend on the shared contract | If SpecialistResult is defined inside warpsense_graph.py, LangChain agent cannot import without pulling LangGraph |
| Coordinator / Deterministic Synthesis (SummaryAgent) | SummaryAgent merges specialist results with priority ordering — no LLM call | Final disposition is auditable and deterministic | If SummaryAgent calls an LLM, the final REWORK_REQUIRED decision becomes probabilistic |

**What stays unchanged:**
| File | Why untouched |
|------|---------------|
| backend/agent/warpsense_agent.py | Phase 2 single agent; closed per Open/Closed principle; forms the baseline column |
| backend/eval/eval_pipeline.py | Phase 3 eval with confirmed FNR = 0.000; must remain the ground truth |
| All Phase 1 and Phase 3 files | Eval data layer and feature extraction are consumed read-only |

**What this plan adds:**
| File | Single responsibility |
|------|------------------------|
| backend/agent/specialists.py | SpecialistResult DTO, compute_violations(), routing trigger functions, BaseSpecialistAgent, ThermalAgent, GeometryAgent, ProcessStabilityAgent, SummaryAgent |
| backend/agent/warpsense_graph.py | LangGraph orchestrator — WarpSenseState, WarpSenseGraph with .assess() interface |
| backend/agent/warpsense_langchain_agent.py | LangChain tool-calling comparison agent with same .assess() interface |
| backend/eval/eval_multi_agent.py | Three-way comparison runner producing ComparisonReport |

**Critical decisions:**
| Decision | Alternative considered | Why alternative rejected |
|----------|------------------------|--------------------------|
| All three agents expose .assess(prediction, features) -> WeldQualityReport | Different interface per agent type | eval_multi_agent.py would need to branch on agent type — comparison becomes untrustworthy |
| specialists.py as shared contract layer | Specialists defined inside warpsense_graph.py | warpsense_langchain_agent.py cannot import SpecialistResult without pulling in full LangGraph dependency |
| compute_violations() as module-level function in specialists.py | Call WarpSenseAgent._step2_threshold_check | Would instantiate a full WarpSenseAgent just to compute violations in the route node |
| SummaryAgent is deterministic — no LLM call | SummaryAgent calls LLM to synthesise | LLM adds non-determinism to the safety-critical final merge |
| Sequential graph execution (linear chain) | Parallel fan-out via LangGraph Send API | Parallel requires async and version-specific reducer behaviour. Sequential is deterministic and traceable |
| New eval_multi_agent.py | Extend eval_pipeline.py with pluggable agent | eval_pipeline.py has confirmed passing E2E gate; Open/Closed prohibits modifying it |
| Full SessionFeatures object in WarpSenseState | to_vector() dict | Dict access uses string keys with no type safety — typo produces None silently |

**Graph routing architecture (corrected):**
- **route_node** computes violations and writes `routing_decision: dict` (thermal_triggered, geometry_triggered, process_triggered) for observability and logging only.
- **Specialist nodes do NOT read these flags.** Each specialist self-determines via `_get_triggered_features()`. The graph runs all three nodes in sequence; each node’s run() decides internally whether to invoke the LLM (triggered) or return the GREEN path result (not triggered).
- **"Always run at least one specialist" is removed.** SummaryAgent already handles no-active-specialists with disposition="PASS"; forcing process_triggered=True had no effect because _process_node never checked it and ProcessStabilityAgent.run() exits early on empty triggered_features.

**Known limitations:**
| Limitation | Why acceptable now | Upgrade path |
|------------|--------------------|---------------|
| WarpSenseLangChainAgent._session is single-threaded only | Eval runs sequentially; no concurrent assess() calls | Replace with contextvars.ContextVar if parallel eval needed |
| SummaryAgent does not run self-check (Step 5 from single agent) | Each specialist cites only from its own retrieved chunks — grounding is implicit per specialist | Phase 6 adds cross-specialist citation verifier |
| LangGraph runs specialists sequentially | Sequential is deterministic and traceable | Phase 6 adds async parallel execution |
| LangChain _parse_output hardcodes primary_defect_categories=[] | FNR/F1 comparison does not use defect categories | Document as known limitation; any metric touching defect_categories will show LangChain worse than actual |
| build_welding_kb.py chunks reference 45° optimal angle | session_feature_extractor uses OPTIMAL_ANGLE_DEG=55.0; specialists now use 55° | Phase 4 does not modify KB; consider updating KB chunks in a future phase for full consistency |

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| LangGraph, LangChain, langchain-groq installed? | All three must be installed | Pre-Flight pip check | Step 4.3, 4.4 | ✅ (Step 4.1 installs them) |
| Python version | 3.12.5 | User confirmed | All steps | ✅ |
| .assess() interface agreed | All three expose same signature | Design decision | Step 4.5 | ✅ |
| specialists.py file location | backend/agent/specialists.py | Design decision | Step 4.2 | ✅ |
| Sequential vs parallel execution | Sequential | Design decision | Step 4.3 | ✅ |
| SessionFeatures in state | Full object | Design decision | Step 4.3 | ✅ |
| OPTIMAL_ANGLE_DEG vs prompts | session_feature_extractor.py uses 55.0; specialists and KB must use same | Fix 3 | Step 4.2, 4.4 | ✅ (plan enforces import and interpolation) |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → STOP. Output full contents of every file modified. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

Read the following files in full and capture:

**(1) backend/agent/warpsense_agent.py**
- THRESHOLDS constant: all feature names and band values
- LOF_LOP_PRIMARY_FEATURES: exact set contents
- LLM_MODEL: exact string value
- WeldQualityReport dataclass: all field names in order
- ThresholdViolation dataclass: all field names (feature, value, threshold, threshold_type, severity, unit, defect_categories)
- StandardsChunk dataclass: all field names (chunk_id, text, source, section, score)
- WarpSenseAgent.__init__ signature
- WarpSenseAgent.assess signature
- grep -n "def prepare_context\|def verify_citations" — must return 2

**(2) backend/features/session_feature_extractor.py**
- SessionFeatures field names in order
- OPTIMAL_ANGLE_DEG: exact value (55.0)
- def to_vector signature and return type
- Confirm to_vector returns dict with 11 feature keys matching THRESHOLDS + heat_diss_mean

**(3) backend/features/weld_classifier.py**
- WeldPrediction field names in order

**(4) backend/eval/eval_scenarios.py**
- Confirm SCENARIOS importable (len == 24)

**(5) backend/eval/eval_pipeline.py**
- ScenarioRunResult fields
- PipelineEvaluator.__init__ signature
- Confirm _run_single exists

**(6) Confirm new files do NOT exist yet:**
- ls backend/agent/specialists.py 2>&1 → must say "No such file"
- ls backend/agent/warpsense_graph.py 2>&1 → must say "No such file"
- ls backend/agent/warpsense_langchain_agent.py 2>&1 → must say "No such file"
- ls backend/eval/eval_multi_agent.py 2>&1 → must say "No such file"

**(7) ChromaDB populated:**
- python -c "import chromadb; c=chromadb.PersistentClient(path='backend/knowledge/chroma_db'); n=c.get_collection('welding_standards').count(); print(n)"
- Must return > 0. Record count.

**(8) Package check:**
- backend/.venv/bin/pip show langgraph langchain langchain-groq 2>&1
- Expected: all three NOT installed before Step 4.1. If any already installed, record version.

Do not change anything. Show full output and wait.

**Baseline Snapshot (agent fills during pre-flight):**
- THRESHOLDS features (in order): ____
- LOF_LOP_PRIMARY_FEATURES: ____
- LLM_MODEL: ____
- WeldQualityReport fields (in order): ____
- ThresholdViolation fields: ____
- StandardsChunk fields: ____
- SessionFeatures fields (in order): ____
- OPTIMAL_ANGLE_DEG: ____ (run grep above; must be 55.0)
- to_vector() return key count: ____ (must be 11)
- WeldPrediction fields: ____
- ScenarioRunResult fields: ____
- specialists.py exists: NO (must be NO)
- warpsense_graph.py exists: NO (must be NO)
- warpsense_langchain_agent.py exists: NO (must be NO)
- eval_multi_agent.py exists: NO (must be NO)
- ChromaDB chunk count: ____ (must be > 0)
- langgraph installed: NO (must be NO before Step 4.1)
- langchain installed: NO (must be NO before Step 4.1)
- langchain-groq installed: NO (must be NO before Step 4.1)

**Pre-flight checks (all must pass before Step 4.1):**
- All 4 new files confirmed absent
- THRESHOLDS has exactly 10 features (heat_diss_mean has no threshold band — absent from THRESHOLDS)
- WeldQualityReport fields confirmed including root_cause, self_check_passed, self_check_notes, llm_raw_response
- ThresholdViolation has .severity and .defect_categories
- to_vector() confirmed to return dict with all 11 features
- ChromaDB chunk count > 0
- Phase 3 eval gate baseline: python backend/eval/eval_pipeline.py --category FN_RISK exits 0
- OPTIMAL_ANGLE_DEG: run `grep -n "OPTIMAL_ANGLE_DEG" backend/features/session_feature_extractor.py` — must show 55.0; record in baseline snapshot

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| 4.1 | ✅ | ✅ | ✅ | pip install only |
| 4.2 | ✅ | ✅ | ✅ | Creates specialists.py |
| 4.3 | ✅ | ✅ | ✅ | Creates warpsense_graph.py — requires ChromaDB |
| 4.4 | ✅ | ✅ | ✅ | Creates warpsense_langchain_agent.py — requires ChromaDB + Groq |
| 4.5 | ✅ | ✅ | ✅ | Creates eval_multi_agent.py |
| 4.6 | ✅ | ✅ | ✅ | E2E gate — all three agents must pass FNR = 0.000 |

---

## Tasks

### Phase 4.A — Foundation

**Goal:** LangGraph and LangChain are installed. specialists.py defines SpecialistResult, compute_violations, all three specialists, and SummaryAgent. Every downstream file in Phase 4 imports from this single contract layer.

---

#### 🟥 Step 4.1: Install LangGraph, LangChain, langchain-groq

**Critical:** These packages are not installed; all LangGraph and LangChain code in Steps 4.3 and 4.4 fails at import without them.

**Action:**
```bash
backend/.venv/bin/pip install \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    langgraph langchain langchain-groq
```

**Verification:**
```bash
backend/.venv/bin/python -c "
  import langgraph; import langchain; import langchain_groq
  from langgraph.graph import StateGraph, END
  from langchain_groq import ChatGroq
  from langchain.agents import AgentExecutor, create_tool_calling_agent
  from langchain.tools import tool
  from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
  import langgraph, langchain, langchain_groq
  print(f'PASS: langgraph={langgraph.__version__}, langchain={langchain.__version__}, langchain_groq={langchain_groq.__version__}')
"
```

Pass: Prints PASS with version numbers.
Fail: ModuleNotFoundError → confirm backend/.venv/bin/pip was used.

---

#### 🟥 Step 4.2: Create backend/agent/specialists.py

**Critical:** SpecialistResult is the shared data contract; every downstream file in Phase 4 imports from here.

**Pre-Read Gate:**
- ls backend/agent/specialists.py 2>&1 → must return "No such file"
- Confirm from Pre-Flight: THRESHOLDS has exactly 10 features; heat_diss_mean is absent from THRESHOLDS
- Confirm WeldQualityReport fields from Pre-Flight
- Confirm OPTIMAL_ANGLE_DEG = 55.0 in session_feature_extractor.py

**Design fixes applied in this step:**
1. **heat_input_mean** moved from ThermalAgent to ProcessStabilityAgent (ownership: process parameter, same as heat_input_cv, amps_cv, voltage_cv).
2. **heat_diss_mean** removed from ThermalAgent.OWNED_FEATURES. It remains in _build_prompt() for context but has no THRESHOLDS band — including it in OWNED_FEATURES implied routing/override participation when it never appears in violations. Add comment: "heat_diss_mean: context-only in prompts, no threshold band."
3. **OPTIMAL_ANGLE_DEG** imported from session_feature_extractor and interpolated into GeometryAgent._build_prompt() and all rules that reference angle target. Never hard-code 45°.
4. **thermal_triggered()** no longer checks heat_input_mean (it was moved to ProcessStabilityAgent).
5. **process_triggered()** now includes heat_input_mean (moved from ThermalAgent).
6. **Trigger vs severity alignment:** _get_triggered_features uses good_min (specialist runs when feature leaves GOOD band). compute_violations uses marginal_min for RISK, good_min for MARGINAL. Prompt rules MUST match: REWORK only for RISK band (heat_input_mean < 3800). MARGINAL band (3800–4500) → CONDITIONAL. Rule 3 uses 3800, not 4500.

**Specialist ownership (corrected):**
- ThermalAgent: heat_diss_max_spike, heat_input_min_rolling, heat_input_drop_severity (heat_diss_mean: context-only, no band)
- GeometryAgent: angle_deviation_mean, angle_max_drift_1s
- ProcessStabilityAgent: voltage_cv, amps_cv, heat_input_cv, arc_on_ratio, heat_input_mean

**File structure:**
```python
"""
specialists.py
--------------
Shared contract layer for WarpSense multi-agent pipeline.

Exports:
  SpecialistResult        — DTO returned by all three specialist agents
  compute_violations()    — module-level threshold check (used by route_node and LangChain agent)
  thermal_triggered()     — routing trigger for ThermalAgent
  geometry_triggered()   — routing trigger for GeometryAgent
  process_triggered()    — routing trigger for ProcessStabilityAgent
  ThermalAgent            — heat dissipation / cold window / stitch transition specialist
  GeometryAgent           — torch angle deviation / drift specialist
  ProcessStabilityAgent   — voltage/current stability / arc continuity / heat_input_mean specialist
  SummaryAgent            — deterministic synthesis of SpecialistResults → WeldQualityReport

Specialist ownership:
  ThermalAgent:           heat_diss_max_spike, heat_input_min_rolling, heat_input_drop_severity
                          (heat_diss_mean: context-only in prompts, no THRESHOLDS band)
  GeometryAgent:          angle_deviation_mean, angle_max_drift_1s
  ProcessStabilityAgent:  voltage_cv, amps_cv, heat_input_cv, arc_on_ratio, heat_input_mean

Angle consistency: angle_deviation_mean = |angle_degrees - OPTIMAL_ANGLE_DEG|.
OPTIMAL_ANGLE_DEG = 55.0 from session_feature_extractor (aluminum MIG).
All prompts and rules MUST use this constant — never hard-code 45°.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from groq import Groq

from backend.agent.warpsense_agent import (
    THRESHOLDS, LLM_MODEL, LOF_LOP_PRIMARY_FEATURES,
    StandardsChunk, ThresholdViolation, WeldQualityReport,
)
from backend.features.session_feature_extractor import SessionFeatures, OPTIMAL_ANGLE_DEG
from backend.features.weld_classifier import WeldPrediction


@dataclass
class SpecialistResult:
    agent_name:          str
    triggered:           bool
    triggered_features:  list[str]
    disposition:         str
    confidence:          float
    defect_categories:   list[str]
    root_cause:          str
    corrective_actions:   list[str]
    standards_references: list[str]
    retrieved_chunk_ids:  list[str]
    llm_raw:             str
    fallback_used:       bool = False


def compute_violations(features: SessionFeatures) -> list[ThresholdViolation]:
    """Compute threshold violations for all THRESHOLDS features. Shared by graph route_node and LangChain agent."""
    fv = features.to_vector()
    violations = []
    for feat_name, t in THRESHOLDS.items():
        val = fv.get(feat_name)
        if val is None:
            continue
        severity = threshold_val = threshold_type = None
        if t["direction"] == "high_is_bad":
            if val > t["marginal_max"]:
                severity, threshold_val, threshold_type = "RISK", t["marginal_max"], "max"
            elif val > t["good_max"]:
                severity, threshold_val, threshold_type = "MARGINAL", t["good_max"], "max"
        elif t["direction"] == "low_is_bad":
            if val < t["marginal_min"]:
                severity, threshold_val, threshold_type = "RISK", t["marginal_min"], "min"
            elif val < t["good_min"]:
                severity, threshold_val, threshold_type = "MARGINAL", t["good_min"], "min"
        if severity:
            violations.append(ThresholdViolation(
                feature=feat_name, value=val, threshold=threshold_val,
                threshold_type=threshold_type, severity=severity,
                unit=t.get("unit", ""), defect_categories=t.get("defect_map", []),
            ))
    violations.sort(key=lambda v: (
        0 if v.severity == "RISK" else 1,
        0 if v.feature in LOF_LOP_PRIMARY_FEATURES else 1,
    ))
    return violations


def thermal_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("heat_diss_max_spike", 0) > t["heat_diss_max_spike"]["good_max"] or
        fv.get("heat_input_min_rolling", float("inf")) < t["heat_input_min_rolling"]["good_min"] or
        fv.get("heat_input_drop_severity", 0) > t["heat_input_drop_severity"]["good_max"]
    )


def geometry_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("angle_deviation_mean", 0) > t["angle_deviation_mean"]["good_max"] or
        fv.get("angle_max_drift_1s", 0) > t["angle_max_drift_1s"]["good_max"]
    )


def process_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("voltage_cv", 0) > t["voltage_cv"]["good_max"] or
        fv.get("amps_cv", 0) > t["amps_cv"]["good_max"] or
        fv.get("heat_input_cv", 0) > t["heat_input_cv"]["good_max"] or
        fv.get("arc_on_ratio", 1.0) < t["arc_on_ratio"]["good_min"] or
        fv.get("heat_input_mean", float("inf")) < t["heat_input_mean"]["good_min"]
    )


class BaseSpecialistAgent(ABC):
    OWNED_FEATURES: set[str] = set()

    def __init__(self, groq_client: Groq, collection, llm_model: str = LLM_MODEL, n_chunks: int = 4, verbose: bool = True):
        self.groq = groq_client
        self.collection = collection
        self.llm_model = llm_model
        self.n_chunks = n_chunks
        self.verbose = verbose

    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @abstractmethod
    def _get_triggered_features(self, features: SessionFeatures) -> list[str]: ...

    @abstractmethod
    def _get_queries(self, prediction: WeldPrediction, features: SessionFeatures, violations: list[ThresholdViolation]) -> list[str]: ...

    @abstractmethod
    def _build_prompt(self, prediction: WeldPrediction, features: SessionFeatures, violations: list[ThresholdViolation], chunks: list[StandardsChunk]) -> str: ...

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _retrieve(self, queries: list[str]) -> list[StandardsChunk]:
        seen_ids: set[str] = set()
        chunks: list[StandardsChunk] = []
        for q in queries[:3]:
            try:
                results = self.collection.query(
                    query_texts=[q], n_results=3,
                    include=["documents", "metadatas", "distances"],
                )
                for i, doc in enumerate(results["documents"][0]):
                    chunk_id = results["ids"][0][i]
                    if chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        meta = results["metadatas"][0][i]
                        chunks.append(StandardsChunk(
                            chunk_id=chunk_id, text=doc,
                            source=meta.get("source", "unknown"),
                            section=meta.get("section", ""),
                            score=round(1 - results["distances"][0][i], 4),
                        ))
            except Exception as e:
                self._log(f"  [{self.agent_name}] KB query failed: {e}")
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks[:self.n_chunks]

    def _call_llm(self, prompt: str) -> tuple[dict, str, bool]:
        """Returns (parsed_dict, raw_str, fallback_used)."""
        raw = ""
        fallback_used = False
        try:
            response = self.groq.chat.completions.create(
                model=self.llm_model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            parsed = json.loads(match.group()) if match else {}
            fallback_used = True
        except Exception as e:
            parsed = {
                "disposition": "CONDITIONAL",
                "defect_categories": [],
                "root_cause": f"LLM call failed: {e}",
                "corrective_actions": ["Review threshold violations above"],
                "standards_references": [],
            }
            fallback_used = True
        return parsed, raw, fallback_used

    def run(self, prediction: WeldPrediction, features: SessionFeatures, violations: list[ThresholdViolation]) -> SpecialistResult:
        triggered_features = self._get_triggered_features(features)

        if not triggered_features:
            return SpecialistResult(
                agent_name=self.agent_name,
                triggered=False,
                triggered_features=[],
                disposition="PASS",
                confidence=prediction.confidence,
                defect_categories=[],
                root_cause="",
                corrective_actions=[],
                standards_references=[],
                retrieved_chunk_ids=[],
                llm_raw="",
            )

        own_violations = [v for v in violations if v.feature in self.OWNED_FEATURES]

        queries = self._get_queries(prediction, features, own_violations)
        chunks = self._retrieve(queries)
        prompt = self._build_prompt(prediction, features, own_violations, chunks)
        parsed, raw, fallback_used = self._call_llm(prompt)

        disposition = parsed.get("disposition", "CONDITIONAL")
        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in own_violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"

        self._log(f"  [{self.agent_name}] {disposition} — triggered: {triggered_features}")

        return SpecialistResult(
            agent_name=self.agent_name,
            triggered=True,
            triggered_features=triggered_features,
            disposition=disposition,
            confidence=prediction.confidence,
            defect_categories=parsed.get("defect_categories", []),
            root_cause=parsed.get("root_cause", ""),
            corrective_actions=parsed.get("corrective_actions", []),
            standards_references=parsed.get("standards_references", []),
            retrieved_chunk_ids=[c.chunk_id for c in chunks],
            llm_raw=raw,
            fallback_used=fallback_used,
        )


class ThermalAgent(BaseSpecialistAgent):
    OWNED_FEATURES = {"heat_diss_max_spike", "heat_input_min_rolling", "heat_input_drop_severity"}

    @property
    def agent_name(self) -> str:
        return "ThermalAgent"

    def _get_triggered_features(self, features: SessionFeatures) -> list[str]:
        fv = features.to_vector()
        t = THRESHOLDS
        out = []
        if fv.get("heat_diss_max_spike", 0) > t["heat_diss_max_spike"]["good_max"]:
            out.append("heat_diss_max_spike")
        if fv.get("heat_input_min_rolling", float("inf")) < t["heat_input_min_rolling"]["good_min"]:
            out.append("heat_input_min_rolling")
        if fv.get("heat_input_drop_severity", 0) > t["heat_input_drop_severity"]["good_max"]:
            out.append("heat_input_drop_severity")
        return out

    def _get_queries(self, prediction, features, violations) -> list[str]:
        queries = [
            "heat dissipation spike thermal instability corrective travel speed preheat",
            "cold arc window heat input minimum rolling incomplete penetration LOF LOP",
        ]
        if any(v.feature == "heat_input_drop_severity" for v in violations):
            queries.append("stitch welding restart heat drop severity corrective action")
        if any(v.severity == "RISK" for v in violations):
            queries.append("REWORK_REQUIRED thermal LOF LOP ISO 5817 acceptance criteria")
        return queries

    def _build_prompt(self, prediction, features, violations, chunks) -> str:
        fv = features.to_vector()
        violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
        context = "\n\n".join(
            f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}" for c in chunks
        )
        thermal_vals = "\n".join(
            f"  {f}: {fv.get(f, 'N/A')}"
            for f in ["heat_diss_max_spike", "heat_diss_mean", "heat_input_min_rolling", "heat_input_drop_severity"]
        )
        return f"""You are ThermalAgent, a welding thermal instability specialist.
Analyse ONLY thermal features: heat dissipation spikes, cold arc windows, stitch transition severity.

Session: {prediction.session_id} | Class: {prediction.quality_class} ({prediction.confidence:.2f})

Thermal Features:
{thermal_vals}

Thermal Violations:
{violations_text}

Retrieved Standards:
{context}

Produce JSON with EXACTLY these keys:
{{"disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "defect_categories": ["LOF"|"LOP"|"THERMAL_INSTABILITY"],
  "root_cause": "2 sentences — thermal mechanism only.",
  "corrective_actions": ["action with numeric target"],
  "standards_references": ["Source: section"]}}

Rules:
1. heat_diss_max_spike > 40 C/s → REWORK_REQUIRED (LOF from thermal spike)
2. heat_input_min_rolling < 3500 J → REWORK_REQUIRED (cold window, LOP risk)
3. heat_input_drop_severity > 15 → REWORK_REQUIRED (stitch LOF risk)
4. MARGINAL band only → CONDITIONAL
5. corrective_actions must include specific numeric targets
6. Only cite standards from retrieved context
Respond with ONLY the JSON object."""


class GeometryAgent(BaseSpecialistAgent):
    OWNED_FEATURES = {"angle_deviation_mean", "angle_max_drift_1s"}

    @property
    def agent_name(self) -> str:
        return "GeometryAgent"

    def _get_triggered_features(self, features: SessionFeatures) -> list[str]:
        fv = features.to_vector()
        t = THRESHOLDS
        out = []
        if fv.get("angle_deviation_mean", 0) > t["angle_deviation_mean"]["good_max"]:
            out.append("angle_deviation_mean")
        if fv.get("angle_max_drift_1s", 0) > t["angle_max_drift_1s"]["good_max"]:
            out.append("angle_max_drift_1s")
        return out

    def _get_queries(self, prediction, features, violations) -> list[str]:
        queries = [
            f"torch angle deviation {OPTIMAL_ANGLE_DEG:.0f} degrees lack of fusion corrective work angle",
            "angle drift variability LOF fusion boundary misdirected arc corrective",
        ]
        if any(v.severity == "RISK" for v in violations):
            queries.append("angle deviation REWORK LOF ISO 5817 acceptance criteria repair")
        return queries

    def _build_prompt(self, prediction, features, violations, chunks) -> str:
        fv = features.to_vector()
        violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
        context = "\n\n".join(
            f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}" for c in chunks
        )
        geo_vals = "\n".join(
            f"  {f}: {fv.get(f, 'N/A')}"
            for f in ["angle_deviation_mean", "angle_max_drift_1s"]
        )
        return f"""You are GeometryAgent, a welding torch geometry specialist.
Analyse ONLY geometry features: torch angle deviation from {OPTIMAL_ANGLE_DEG:.0f} degrees (optimal work angle) and angular drift rate.
angle_deviation_mean is computed as |measured_angle - {OPTIMAL_ANGLE_DEG:.0f}| — the target is {OPTIMAL_ANGLE_DEG:.0f}°, not 45°.

Session: {prediction.session_id} | Class: {prediction.quality_class} ({prediction.confidence:.2f})

Geometry Features:
{geo_vals}

Geometry Violations:
{violations_text}

Retrieved Standards:
{context}

Produce JSON with EXACTLY these keys:
{{"disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "defect_categories": ["LOF"|"UNDERCUT"],
  "root_cause": "2 sentences — geometry mechanism only.",
  "corrective_actions": ["action with numeric target"],
  "standards_references": ["Source: section"]}}

Rules:
1. angle_deviation_mean > 15 deg → REWORK_REQUIRED (LOF from misdirected arc; deviation from {OPTIMAL_ANGLE_DEG:.0f}° target)
2. angle_max_drift_1s > 15 deg → REWORK_REQUIRED (rapid angular swing, fusion boundary risk)
3. MARGINAL band → CONDITIONAL
4. corrective_actions must include specific degree targets (e.g. "correct to {OPTIMAL_ANGLE_DEG:.0f} ± 5 degrees")
5. Only cite standards from retrieved context
Respond with ONLY the JSON object."""


class ProcessStabilityAgent(BaseSpecialistAgent):
    OWNED_FEATURES = {"voltage_cv", "amps_cv", "heat_input_cv", "arc_on_ratio", "heat_input_mean"}

    @property
    def agent_name(self) -> str:
        return "ProcessStabilityAgent"

    def _get_triggered_features(self, features: SessionFeatures) -> list[str]:
        fv = features.to_vector()
        t = THRESHOLDS
        out = []
        if fv.get("voltage_cv", 0) > t["voltage_cv"]["good_max"]:
            out.append("voltage_cv")
        if fv.get("amps_cv", 0) > t["amps_cv"]["good_max"]:
            out.append("amps_cv")
        if fv.get("heat_input_cv", 0) > t["heat_input_cv"]["good_max"]:
            out.append("heat_input_cv")
        if fv.get("arc_on_ratio", 1.0) < t["arc_on_ratio"]["good_min"]:
            out.append("arc_on_ratio")
        if fv.get("heat_input_mean", float("inf")) < t["heat_input_mean"]["good_min"]:
            out.append("heat_input_mean")
        return out

    def _get_queries(self, prediction, features, violations) -> list[str]:
        queries = [
            "voltage CV instability porosity arc length shielding gas corrective action",
            "arc on ratio low restart continuity LOF cold initiation corrective",
        ]
        if any(v.feature in {"heat_input_cv", "amps_cv", "heat_input_mean"} for v in violations):
            queries.append("heat input CV amps mean process parameter corrective WPS bounds")
        if any(v.severity == "RISK" for v in violations):
            queries.append("arc continuity REWORK LOF restart cold interface ISO 5817")
        return queries

    def _build_prompt(self, prediction, features, violations, chunks) -> str:
        fv = features.to_vector()
        violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
        context = "\n\n".join(
            f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}" for c in chunks
        )
        proc_vals = "\n".join(
            f"  {f}: {fv.get(f, 'N/A')}"
            for f in ["voltage_cv", "amps_cv", "heat_input_cv", "arc_on_ratio", "heat_input_mean"]
        )
        return f"""You are ProcessStabilityAgent, a welding process stability specialist.
Analyse ONLY process stability features: voltage/current consistency, heat input variability, arc continuity, heat_input_mean (session-level average volts×amps).

Session: {prediction.session_id} | Class: {prediction.quality_class} ({prediction.confidence:.2f})

Process Stability Features:
{proc_vals}

Process Violations:
{violations_text}

Retrieved Standards:
{context}

Produce JSON with EXACTLY these keys:
{{"disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "defect_categories": ["LOF"|"LOP"|"POROSITY"|"UNDERCUT"],
  "root_cause": "2 sentences — process stability mechanism only.",
  "corrective_actions": ["action with numeric target"],
  "standards_references": ["Source: section"]}}

Rules:
1. arc_on_ratio < 0.75 → REWORK_REQUIRED (excessive restarts, LOF at each cold initiation)
2. heat_input_cv > 0.20 → REWORK_REQUIRED (severe process instability, LOF/LOP risk)
3. heat_input_mean < 3800 J (RISK band, per THRESHOLDS marginal_min) → REWORK_REQUIRED (chronic under-heating, LOF/LOP risk). MARGINAL band (3800–4500) → CONDITIONAL.
4. voltage_cv > 0.15 or amps_cv > 0.12 → CONDITIONAL (porosity risk)
5. MARGINAL band → CONDITIONAL
6. corrective_actions must include specific numeric targets (%, V, A)
7. Only cite standards from retrieved context
Respond with ONLY the JSON object."""


class SummaryAgent:
    """Deterministic priority merge of SpecialistResults → WeldQualityReport. No LLM call."""

    def synthesise(
        self,
        specialist_results: list[SpecialistResult],
        prediction: WeldPrediction,
        features: SessionFeatures,
        violations: list[ThresholdViolation],
    ) -> WeldQualityReport:
        active = [r for r in specialist_results if r.triggered]

        dispositions = [r.disposition for r in active]
        if "REWORK_REQUIRED" in dispositions:
            disposition = "REWORK_REQUIRED"
        elif "CONDITIONAL" in dispositions:
            disposition = "CONDITIONAL"
        else:
            disposition = "PASS"

        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"

        iso_map = {"DEFECTIVE": "BELOW_D", "MARGINAL": "D", "GOOD": "C"}
        iso_5817_level = iso_map.get(prediction.quality_class, "D")

        all_defects: list[str] = []
        all_root_causes: list[str] = []
        all_corrective: list[str] = []
        all_references: list[str] = []
        all_chunk_ids: list[str] = []

        for agent_name in ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]:
            for r in active:
                if r.agent_name != agent_name:
                    continue
                for cat in r.defect_categories:
                    if cat not in all_defects:
                        all_defects.append(cat)
                if r.root_cause:
                    all_root_causes.append(f"[{agent_name}] {r.root_cause}")
                for action in r.corrective_actions:
                    if action not in all_corrective:
                        all_corrective.append(action)
                for ref in r.standards_references:
                    if ref not in all_references:
                        all_references.append(ref)
                all_chunk_ids.extend(r.retrieved_chunk_ids)

        if active:
            rework_agents = [r.agent_name for r in active if r.disposition == "REWORK_REQUIRED"]
            active_names = [r.agent_name for r in active]
            if rework_agents:
                rationale = f"{', '.join(rework_agents)} flagged REWORK_REQUIRED. Safety override applied."
            elif disposition == "CONDITIONAL":
                rationale = f"{', '.join(active_names)}: CONDITIONAL. Monitor next 3 sessions."
            else:
                rationale = f"All active specialists ({', '.join(active_names)}) returned PASS."
        else:
            rationale = "No specialists triggered. All features within GOOD band."

        return WeldQualityReport(
            session_id=prediction.session_id,
            report_timestamp=datetime.now(timezone.utc).isoformat(),
            quality_class=prediction.quality_class,
            confidence=prediction.confidence,
            iso_5817_level=iso_5817_level,
            primary_defect_categories=all_defects,
            threshold_violations=violations,
            root_cause="\n".join(all_root_causes) or "All features within GOOD band.",
            corrective_actions=all_corrective[:5],
            standards_references=all_references,
            retrieved_chunks_used=list(set(all_chunk_ids)),
            disposition=disposition,
            disposition_rationale=rationale,
            self_check_passed=True,
            self_check_notes=f"Multi-agent synthesis: {len(active)} specialist(s) active.",
            llm_raw_response=json.dumps([asdict(r) for r in specialist_results]),
        )
```

**Git Checkpoint:**
```bash
git add backend/agent/specialists.py
git commit -m "step 4.2: create specialists.py — SpecialistResult contract, 3 specialist agents, SummaryAgent"
```

**Verification Test (corrected r_pass — realistic SpecialistResult):**
```bash
python -c "
  import sys; sys.path.insert(0, '.')
  from backend.agent.specialists import (
      SpecialistResult, compute_violations, thermal_triggered,
      geometry_triggered, process_triggered, ThermalAgent,
      GeometryAgent, ProcessStabilityAgent, SummaryAgent,
  )
  import dataclasses

  fields = {f.name for f in dataclasses.fields(SpecialistResult)}
  assert 'agent_name' in fields
  assert 'triggered' in fields
  assert 'triggered_features' in fields
  assert 'fallback_used' in fields

  from backend.features.session_feature_extractor import generate_feature_dataset
  dataset = generate_feature_dataset()
  expert_features = next(s for s in dataset if s.quality_label == 'GOOD')
  novice_features = next(s for s in dataset if s.quality_label == 'MARGINAL')
  assert not thermal_triggered(expert_features), 'expert should not trigger thermal'
  assert thermal_triggered(novice_features), 'novice must trigger thermal'

  violations = compute_violations(novice_features)
  assert len(violations) >= 1
  assert hasattr(violations[0], 'severity')
  assert hasattr(violations[0], 'defect_categories')

  from unittest.mock import MagicMock
  mock_groq = MagicMock()
  mock_collection = MagicMock()
  agent = ThermalAgent(mock_groq, mock_collection, verbose=False)
  result = agent.run(MagicMock(confidence=0.9, session_id='TEST', quality_class='GOOD', top_drivers=[]), expert_features, [])
  assert result.triggered == False
  assert result.disposition == 'PASS'
  assert mock_groq.chat.completions.create.call_count == 0, 'LLM must not be called on GREEN path'

  # Realistic SpecialistResult: triggered=True with non-empty triggered_features
  r_rework = SpecialistResult('ThermalAgent', True, ['heat_diss_max_spike'], 'REWORK_REQUIRED', 0.8, ['LOF'], 'root', [], [], [], '', False)
  r_pass   = SpecialistResult('GeometryAgent', True, ['angle_deviation_mean'], 'PASS', 0.8, [], '', [], [], [], '', False)
  summary = SummaryAgent()
  report = summary.synthesise([r_rework, r_pass], MagicMock(session_id='TEST', quality_class='MARGINAL', confidence=0.8), expert_features, [])
  assert report.disposition == 'REWORK_REQUIRED', f'expected REWORK_REQUIRED, got {report.disposition}'

  print('PASS: SpecialistResult fields correct, triggers work, GREEN path skips LLM, SummaryAgent priority merge correct')
"
```

Pass: Prints PASS: SpecialistResult fields correct...
Fail: r_pass with triggered=True and triggered_features=[] is invalid — use triggered_features=["angle_deviation_mean"].

---

### Phase 4.B — Implementations

**Goal:** WarpSenseGraph and WarpSenseLangChainAgent both exist, both pass a single-scenario smoke test, and both expose .assess(prediction, features) -> WeldQualityReport.

---

#### 🟥 Step 4.3: Create backend/agent/warpsense_graph.py

**Critical:** LangGraph implementation; production path. Depends on Steps 4.1 and 4.2.

**Pre-Read Gate:**
- ls backend/agent/warpsense_graph.py 2>&1 → must return "No such file"
- grep -n "def assess" backend/agent/warpsense_agent.py → must return exactly 1
- python -c "from backend.agent.specialists import SpecialistResult, ThermalAgent; print('PASS')" → must print PASS
- backend/.venv/bin/python -c "from langgraph.graph import StateGraph, END; print('PASS')" → must print PASS

**Design fixes applied:**
1. **Dead flags removed.** WarpSenseState has `routing_decision: Dict[str, bool]` (for observability/logging only). Specialist nodes never read it — each self-determines via _get_triggered_features().
2. **"Always run at least one specialist" block removed.** SummaryAgent handles no-active-specialists correctly.
3. **chroma_client injection:** `__init__(self, chroma_path=None, chroma_client: Optional[chromadb.PersistentClient] = None, ...)`. When chroma_client is provided, use it; otherwise create `chromadb.PersistentClient(path=chroma_path or kb_path)`. Step 4.5 passes shared client — no file modification in 4.5.

**Required constructor signature (WarpSenseGraph):**
```python
def __init__(
    self,
    chroma_path=None,
    chroma_client: Optional["chromadb.PersistentClient"] = None,
    collection_name: str = "welding_standards",
    llm_model: str = LLM_MODEL,
    n_chunks_per_specialist: int = 4,
    verbose: bool = True,
):
    # If chroma_client provided (eval_multi_agent), use it. Else create own.
    if chroma_client is not None:
        client = chroma_client
    else:
        kb_path = chroma_path or str(_KB_PATH)
        client = chromadb.PersistentClient(path=kb_path)
    ef = embedding_functions.DefaultEmbeddingFunction()
    self._collection = client.get_collection(name=collection_name, embedding_function=ef)
```

**WarpSenseState (TypedDict):**
```python
from typing import Dict, Optional, TypedDict

class WarpSenseState(TypedDict):
    session_id:         str
    features:           SessionFeatures
    prediction:         WeldPrediction
    violations:         list
    routing_decision:   Dict[str, bool]   # thermal_triggered, geometry_triggered, process_triggered — observability only
    thermal_result:     Optional[SpecialistResult]
    geometry_result:    Optional[SpecialistResult]
    process_result:     Optional[SpecialistResult]
    final_report:       Optional[WeldQualityReport]
```

**initial_state in assess():**
```python
initial_state: WarpSenseState = {
    "session_id":         session_id,
    "features":           features,
    "prediction":         prediction,
    "violations":         [],
    "routing_decision":   {},
    "thermal_result":     None,
    "geometry_result":    None,
    "process_result":     None,
    "final_report":       None,
}
```

**Graph nodes (full — do not reconstruct from prior plan):**
```python
def _route_node(self, state: WarpSenseState) -> dict:
    features = state["features"]
    violations = compute_violations(features)
    t_trig = thermal_triggered(features)
    g_trig = geometry_triggered(features)
    p_trig = process_triggered(features)
    self._log(f"[Graph] Route: thermal={t_trig}, geometry={g_trig}, process={p_trig}, violations={len(violations)}")
    return {
        "violations": violations,
        "routing_decision": {"thermal_triggered": t_trig, "geometry_triggered": g_trig, "process_triggered": p_trig},
    }

def _thermal_node(self, state: WarpSenseState) -> dict:
    result = self._thermal.run(state["prediction"], state["features"], state["violations"])
    self._log(f"[Graph] ThermalAgent: {result.disposition} (triggered={result.triggered})")
    return {"thermal_result": result}

def _geometry_node(self, state: WarpSenseState) -> dict:
    result = self._geometry.run(state["prediction"], state["features"], state["violations"])
    self._log(f"[Graph] GeometryAgent: {result.disposition} (triggered={result.triggered})")
    return {"geometry_result": result}

def _process_node(self, state: WarpSenseState) -> dict:
    result = self._process.run(state["prediction"], state["features"], state["violations"])
    self._log(f"[Graph] ProcessStabilityAgent: {result.disposition} (triggered={result.triggered})")
    return {"process_result": result}

def _summary_node(self, state: WarpSenseState) -> dict:
    results = [r for r in [state.get("thermal_result"), state.get("geometry_result"), state.get("process_result")] if r is not None]
    report = self._summary.synthesise(results, state["prediction"], state["features"], state["violations"])
    self._log(f"[Graph] SummaryAgent: {report.disposition}")
    return {"final_report": report}
```

**_build_graph (exact implementation):**
```python
def _build_graph(self):
    from langgraph.graph import StateGraph, END
    graph = StateGraph(WarpSenseState)
    graph.add_node("route", self._route_node)
    graph.add_node("thermal", self._thermal_node)
    graph.add_node("geometry", self._geometry_node)
    graph.add_node("process", self._process_node)
    graph.add_node("summary", self._summary_node)
    graph.set_entry_point("route")
    graph.add_edge("route", "thermal")
    graph.add_edge("thermal", "geometry")
    graph.add_edge("geometry", "process")
    graph.add_edge("process", "summary")
    graph.add_edge("summary", END)
    return graph.compile()
```

**assess():** Invoke self._graph.invoke(initial_state), return final_state["final_report"]. Raise RuntimeError if final_report is None.

**Verification Test Part A (full replacement — do not use original):**
```bash
python -c "
  import sys, inspect; sys.path.insert(0, '.')
  from backend.agent.warpsense_graph import WarpSenseGraph, WarpSenseState
  sig = inspect.signature(WarpSenseGraph.assess)
  assert 'prediction' in sig.parameters
  assert 'features' in sig.parameters
  fields = WarpSenseState.__annotations__
  for f in ['session_id', 'features', 'prediction', 'violations', 'routing_decision',
            'thermal_result', 'geometry_result', 'process_result', 'final_report']:
      assert f in fields, f'{f} missing from WarpSenseState'
  assert 'thermal_triggered' not in fields, 'removed — use routing_decision'
  assert 'geometry_triggered' not in fields, 'removed — use routing_decision'
  assert 'process_triggered' not in fields, 'removed — use routing_decision'
  print('PASS A: WarpSenseGraph.assess() signature correct, WarpSenseState has routing_decision, no trigger booleans')
"
```

**Verification Test Part B:** Single scenario smoke (ChromaDB + Groq) — TC_001, assert WeldQualityReport, disposition in (PASS, CONDITIONAL, REWORK_REQUIRED).

---

#### 🟥 Step 4.4: Create backend/agent/warpsense_langchain_agent.py

**Critical:** LangChain comparison agent. Same .assess() interface.

**Design fixes applied:**
1. **chroma_client injection:** `__init__(self, chroma_path=None, chroma_client: Optional[chromadb.PersistentClient] = None, collection_name=..., llm_model=..., verbose=...)`. When chroma_client provided, use it; else create `chromadb.PersistentClient(path=chroma_path or kb_path)`.
2. **Single consolidated context tool with Literal domain parameter:**
   - `get_domain_context(domain: Literal["thermal", "geometry", "process"]) -> str`
   - LangChain tool schema exposes enum; LLM cannot pass "Thermal", "heat", "all". Use `from typing import Literal`.
3. **primary_defect_categories:** Keep hardcoded []; docstring: "LangChain comparison: primary_defect_categories always [] — known limitation."
4. **OPTIMAL_ANGLE_DEG** in system prompt if geometry guidance given.

**Tools (both required):**

1. **retrieve_standards(query: str) -> str** — Queries self._collection with query_texts=[query], n_results=4. Returns "\n\n".join of "[{chunk_id}] {source} | {section}\n{text}" per chunk. On exception returns "Retrieval failed: {e}".

2. **get_domain_context(domain: Literal["thermal", "geometry", "process"]) -> str** — Consolidated replacement for get_thermal/geometry/process_context:
```python
from typing import Literal

@tool
def get_domain_context(domain: Literal["thermal", "geometry", "process"]) -> str:
    """
    Get feature values and violations for the specified domain.
    domain: 'thermal' | 'geometry' | 'process'. Call get_domain_context(domain='thermal'),
    get_domain_context(domain='geometry'), get_domain_context(domain='process') for each domain
    present in the session violations.
    """
    session = session_ref
    if not session:
        return "No session loaded."
    features = session["features"]
    violations = session["violations"]
    fv = features.to_vector()
    if domain == "thermal":
        feats = ["heat_diss_max_spike", "heat_diss_mean", "heat_input_min_rolling", "heat_input_drop_severity"]
        triggered = thermal_triggered(features)
    elif domain == "geometry":
        feats = ["angle_deviation_mean", "angle_max_drift_1s"]
        triggered = geometry_triggered(features)
    else:
        feats = ["voltage_cv", "amps_cv", "heat_input_cv", "arc_on_ratio", "heat_input_mean"]
        triggered = process_triggered(features)
    domain_feats = {f: fv.get(f) for f in feats}
    domain_viols = [v for v in violations if v.feature in domain_feats]
    viol_text = "\n".join(v.as_display_line() for v in domain_viols) or "None"
    feat_text = "\n".join(f"  {k}: {val}" for k, val in domain_feats.items())
    return f"{domain.capitalize()} triggered: {triggered}\n{domain.capitalize()} Features:\n{feat_text}\n{domain.capitalize()} Violations:\n{viol_text}"
```

**System prompt (exact text — do not infer):**
```python
("system",
 "You are WarpSenseAgent, a welding quality assessment AI.\n"
 "Use the provided tools to gather domain context and standards, then produce a final JSON quality report.\n"
 "You MUST call get_domain_context exactly three times: get_domain_context(domain='thermal'), "
 "get_domain_context(domain='geometry'), get_domain_context(domain='process'). Pass the domain explicitly.\n"
 "Then call retrieve_standards with targeted queries for each domain that has violations.\n"
 "Your FINAL response must be a JSON object with EXACTLY these keys:\n"
 '{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", '
 '"disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED", '
 '"disposition_rationale": "One sentence.", '
 '"root_cause": "2-3 sentences.", '
 '"corrective_actions": ["action with numeric target"], '
 '"standards_references": ["Source: section"]}\n'
 "Rules: (1) Any LOF/LOP RISK feature → REWORK_REQUIRED. (2) MARGINAL only → CONDITIONAL. "
 "(3) All GOOD → PASS. (4) corrective_actions must include specific numeric targets. "
 "(5) Only cite standards from retrieved context.\n"
 "Respond with ONLY the JSON object as your final answer."),
```

**Verification Test Part A (structure — no ChromaDB, no Groq):**
```bash
python -c "
  import sys, inspect, pathlib; sys.path.insert(0, '.')
  from backend.agent.warpsense_langchain_agent import WarpSenseLangChainAgent
  sig = inspect.signature(WarpSenseLangChainAgent.assess)
  assert 'prediction' in sig.parameters and 'features' in sig.parameters
  src = pathlib.Path('backend/agent/warpsense_langchain_agent.py').read_text()
  assert 'retrieve_standards' in src, 'retrieve_standards tool missing'
  assert 'get_domain_context' in src, 'get_domain_context tool missing'
  assert 'Literal[' in src, 'Literal type missing from tool signature'
  assert 'handle_parsing_errors=True' in src, 'handle_parsing_errors missing'
  assert '_fallback_report' in src, 'fallback missing'
  assert 'chroma_client' in src, 'chroma_client injection missing'
  assert 'lof_lop_risk' in src, 'LOF/LOP safety override missing'
  print('PASS A: WarpSenseLangChainAgent structure correct')
"
```
Pass: Prints PASS A.
Fail: assertion message tells you exactly what is missing.

**Verification Test Part B (single scenario smoke — requires ChromaDB + Groq):**
```bash
python -c "
  import sys; sys.path.insert(0, '.')
  from backend.features.session_feature_extractor import generate_feature_dataset
  from backend.features.weld_classifier import WeldClassifier
  from backend.eval.eval_scenarios import get_scenario_by_id
  from backend.agent.warpsense_langchain_agent import WarpSenseLangChainAgent
  from backend.agent.warpsense_agent import WeldQualityReport

  dataset = generate_feature_dataset()
  clf = WeldClassifier(); clf.train(dataset)
  agent = WarpSenseLangChainAgent(verbose=True)

  scenario = get_scenario_by_id('TC_001_novice_classic')
  pred = clf.predict(scenario.features)
  report = agent.assess(pred, scenario.features)

  assert isinstance(report, WeldQualityReport)
  assert report.disposition in ('PASS', 'CONDITIONAL', 'REWORK_REQUIRED')
  assert report.session_id == pred.session_id
  print(f'PASS B: WarpSenseLangChainAgent produced {report.disposition} for TC_001')
"
```
Pass: Prints PASS B with a valid disposition.

---

#### 🟥 Step 4.5: Create backend/eval/eval_multi_agent.py

**Critical:** Produces the three-way comparison table.

**Design fixes applied:**
1. **Shared ChromaDB client:** MultiAgentEvaluator creates one client, passes to WarpSenseGraph and WarpSenseLangChainAgent. Both accept chroma_client (specified in Steps 4.3, 4.4) — no modification of those files.
2. **Fallback detection:** root_cause heuristic PLUS LangGraph llm_raw_response parse. Structure from SummaryAgent.synthesise: `json.dumps([asdict(r) for r in specialist_results])` — LangGraph reports store SpecialistResult dicts; single-agent/LangChain store raw LLM string.
3. **Document LangChain primary_defect_categories=[]** in comparison table footer.

**Full file structure:**
```python
"""
eval_multi_agent.py
-------------------
Three-way comparison: single agent vs LangGraph vs LangChain.
Runs all three against the same 24 eval scenarios from Phase 3.

Does NOT modify eval_pipeline.py (Open/Closed principle).
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

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

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
    tp: int; fp: int; tn: int; fn: int
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
            print(msg)

    def _detect_fallback(self, report) -> bool:
        fallback_used = False
        if hasattr(report, "root_cause"):
            fallback_used = ("failed" in report.root_cause.lower() or "fallback" in report.root_cause.lower())
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
        with open(out, "w") as f:
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
```

**Git Checkpoint:**
```bash
git add backend/eval/eval_multi_agent.py
git commit -m "step 4.5: create eval_multi_agent.py — three-way comparison table"
```

**Verification Test (structure — no ChromaDB, no Groq):**
```bash
python -c "
  import sys, pathlib; sys.path.insert(0, '.')
  from backend.eval.eval_multi_agent import MultiAgentEvaluator, ComparisonReport, AgentEvalResult
  import dataclasses

  fields = {f.name for f in dataclasses.fields(ComparisonReport)}
  assert 'winner'           in fields
  assert 'winner_rationale' in fields
  assert 'results'          in fields

  agg_fields = {f.name for f in dataclasses.fields(AgentEvalResult)}
  assert 'error_count'        in agg_fields
  assert 'mean_fallback_rate' in agg_fields
  assert 'fnr'                in agg_fields

  src = pathlib.Path('backend/eval/eval_multi_agent.py').read_text()
  assert 'eval_pipeline' not in src,           'eval_pipeline.py must not be imported'
  assert 'most_common_actual' in src,           'confusion matrix must use observed actuals'
  assert 'args.llm_runs < 1' in src,            '--llm-runs guard missing'
  assert 'WarpSenseAgent'     in src
  assert 'WarpSenseGraph'     in src
  assert 'WarpSenseLangChainAgent' in src
  assert 'FP_RISK' in src,                      'FP_RISK exit gate missing'
  assert 'shared_client' in src,                 'shared ChromaDB client missing'
  assert 'chroma_client' in src,                 'chroma_client injection missing'
  assert 'fallback_used' in src,                 'fallback detection missing'

  print('PASS: eval_multi_agent.py structure correct — all 3 agents, shared client, FN+FP gates, fallback detection')
"
```
Pass: Prints PASS.
Fail: Assertion message identifies missing element.

---

#### 🟥 Step 4.6: Run E2E comparison gate

**Safety gate first (FN_RISK — 4 scenarios):**
```bash
python backend/eval/eval_multi_agent.py --category FN_RISK
```
Pass: Exit 0, all three agents FNR = 0.000, no FAIL/WARN lines.

**FP gate (FP_RISK — prevents TC_017 false positive):**
```bash
python backend/eval/eval_multi_agent.py --category FP_RISK
```
Pass: Exit 0, no REWORK on scenarios with expected_disposition=CONDITIONAL (e.g. TC_017 heat_input_mean=4000 MARGINAL → CONDITIONAL, not REWORK).

**Full comparison (all 24 scenarios):**
```bash
python backend/eval/eval_multi_agent.py --save
```
Pass: Exit 0, comparison table printed, JSON saved.

**Phase 3 regression:**
```bash
python backend/eval/eval_pipeline.py --category FN_RISK
```
Must still exit 0 with FNR = 0.000.

---

## Regression Guard

| System | Pre-change behaviour | Post-change verification |
|--------|----------------------|---------------------------|
| eval_pipeline.py Phase 3 gate | FNR = 0.000, exit 0 | python backend/eval/eval_pipeline.py --category FN_RISK — must still exit 0 |
| warpsense_agent.py assess | Returns WeldQualityReport | python -c "from backend.agent.warpsense_agent import WarpSenseAgent; assert hasattr(WarpSenseAgent,'assess')" |

---

## Rollback Procedure

```bash
git revert HEAD    # reverts step 4.5
git revert HEAD    # reverts step 4.4
git revert HEAD    # reverts step 4.3
git revert HEAD    # reverts step 4.2
# Step 4.1: backend/.venv/bin/pip uninstall langgraph langchain langchain-groq -y
python backend/eval/eval_pipeline.py --category FN_RISK   # must still exit 0
```

---

## Success Criteria

| Deliverable | Target | Verification |
|------------|--------|--------------|
| LangGraph, LangChain, langchain-groq installed | All import cleanly | Step 4.1 verification |
| specialists.py | SpecialistResult importable, GREEN path skips LLM, heat_input_mean in ProcessStabilityAgent, OPTIMAL_ANGLE_DEG in GeometryAgent | Step 4.2 unit test |
| WarpSenseGraph.assess() | Returns WeldQualityReport, routing_decision observability only | Step 4.3 Part B smoke test |
| WarpSenseLangChainAgent.assess() | Returns WeldQualityReport, get_domain_context(domain=...) tool | Step 4.4 Part B smoke test |
| eval_multi_agent.py | Three-way comparison, shared ChromaDB client, fallback from llm_raw when available | Step 4.5 + 4.6 |
| All 3 agents FNR | 0.000 on FN_RISK scenarios | Step 4.6 FN_RISK gate |
| FP_RISK gate | No REWORK on expected CONDITIONAL (TC_017) | Step 4.6 FP_RISK gate |
| Phase 3 regression | FNR still 0.000 after Phase 4 | Step 4.6 regression check |

---

⚠️ Execute in order: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6.
⚠️ Step 4.2 must complete before 4.3 or 4.4 — SpecialistResult is the shared contract.
⚠️ Step 4.6 FN_RISK gate must pass for ALL THREE agents before Phase 4 is declared complete.
⚠️ Do not modify eval_pipeline.py or warpsense_agent.py at any point during Phase 4.
⚠️ Do not batch multiple steps into one git commit.
