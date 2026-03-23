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

from agent.warpsense_agent import (
    THRESHOLDS,
    LLM_MODEL,
    LOF_LOP_PRIMARY_FEATURES,
    StandardsChunk,
    ThresholdViolation,
    WeldQualityReport,
)
from knowledge.rag_retriever import RAGRetriever, decompose_queries
from features.session_feature_extractor import SessionFeatures, OPTIMAL_ANGLE_DEG
from features.weld_classifier import WeldPrediction

import logging

from prompts.versions import PROMPT_VERSIONS

logger = logging.getLogger(__name__)

# Human-readable display names for threshold features — used in _threshold_fallback()
# corrective actions so the user-facing report never shows raw Python variable names.
_FEATURE_LABELS: dict[str, str] = {
    "heat_diss_max_spike": "peak heat dissipation rate",
    "heat_input_min_rolling": "minimum rolling heat input",
    "heat_input_drop_severity": "heat input drop severity",
    "angle_deviation_mean": "average torch angle deviation",
    "angle_max_drift_1s": "max torch angle drift (1 s)",
    "voltage_cv": "voltage consistency (CV)",
    "amps_cv": "current consistency (CV)",
    "heat_input_cv": "heat input consistency (CV)",
    "arc_on_ratio": "arc continuity ratio",
    "heat_input_mean": "average heat input",
}


@dataclass
class SpecialistResult:
    agent_name: str
    triggered: bool
    triggered_features: list[str]
    disposition: str
    confidence: float
    defect_categories: list[str]
    root_cause: str
    corrective_actions: list[str]
    standards_references: list[str]
    retrieved_chunk_ids: list[str]
    llm_raw: str
    fallback_used: bool = False


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
                severity, threshold_val, threshold_type = (
                    "RISK",
                    t["marginal_max"],
                    "max",
                )
            elif val > t["good_max"]:
                severity, threshold_val, threshold_type = (
                    "MARGINAL",
                    t["good_max"],
                    "max",
                )
        elif t["direction"] == "low_is_bad":
            if val < t["marginal_min"]:
                severity, threshold_val, threshold_type = (
                    "RISK",
                    t["marginal_min"],
                    "min",
                )
            elif val < t["good_min"]:
                severity, threshold_val, threshold_type = (
                    "MARGINAL",
                    t["good_min"],
                    "min",
                )

        if severity:
            violations.append(
                ThresholdViolation(
                    feature=feat_name,
                    value=val,
                    threshold=threshold_val,
                    threshold_type=threshold_type,
                    severity=severity,
                    unit=t.get("unit", ""),
                    defect_categories=t.get("defect_map", []),
                )
            )

    violations.sort(
        key=lambda v: (
            0 if v.severity == "RISK" else 1,
            0 if v.feature in LOF_LOP_PRIMARY_FEATURES else 1,
        )
    )
    return violations


def thermal_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("heat_diss_max_spike", 0) > t["heat_diss_max_spike"]["good_max"]
        or fv.get("heat_input_min_rolling", float("inf"))
        < t["heat_input_min_rolling"]["good_min"]
        or fv.get("heat_input_drop_severity", 0)
        > t["heat_input_drop_severity"]["good_max"]
    )


def geometry_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("angle_deviation_mean", 0) > t["angle_deviation_mean"]["good_max"]
        or fv.get("angle_max_drift_1s", 0) > t["angle_max_drift_1s"]["good_max"]
    )


def process_triggered(features: SessionFeatures) -> bool:
    fv = features.to_vector()
    t = THRESHOLDS
    return (
        fv.get("voltage_cv", 0) > t["voltage_cv"]["good_max"]
        or fv.get("amps_cv", 0) > t["amps_cv"]["good_max"]
        or fv.get("heat_input_cv", 0) > t["heat_input_cv"]["good_max"]
        or fv.get("arc_on_ratio", 1.0) < t["arc_on_ratio"]["good_min"]
        or fv.get("heat_input_mean", float("inf")) < t["heat_input_mean"]["good_min"]
    )


class BaseSpecialistAgent(ABC):
    OWNED_FEATURES: set[str] = set()

    def __init__(
        self,
        groq_client: Groq,
        retriever: RAGRetriever,
        llm_model: str = LLM_MODEL,
        n_chunks: int = 4,
        verbose: bool = True,
    ):
        self.groq = groq_client
        self.retriever = retriever
        self.llm_model = llm_model
        self.n_chunks = n_chunks  # Retained for interface compatibility; retrieval cap is controlled by RAGRetriever.n_results
        self.verbose = verbose

    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @property
    @abstractmethod
    def domain(self) -> str: ...

    # Must return "thermal" | "geometry" | "process"
    # Used by _retrieve() to select the domain anchor query in decompose_queries

    @abstractmethod
    def _get_triggered_features(self, features: SessionFeatures) -> list[str]: ...

    @abstractmethod
    def _get_queries(
        self,
        prediction: WeldPrediction,
        features: SessionFeatures,
        violations: list[ThresholdViolation],
    ) -> list[str]: ...

    @abstractmethod
    def _build_prompt(
        self,
        prediction: WeldPrediction,
        features: SessionFeatures,
        violations: list[ThresholdViolation],
        chunks: list[StandardsChunk],
    ) -> str: ...

    def _log(self, msg: str) -> None:
        if self.verbose:
            logger.info(msg)

    def _retrieve(
        self, queries: list[str], violations: list[ThresholdViolation]
    ) -> list[StandardsChunk]:
        """
        Delegate to RAGRetriever after expanding queries via decompose_queries.
        violations: own_violations for this specialist (list[ThresholdViolation])
        """
        expanded = decompose_queries(queries, violations, self.domain)
        return self.retriever.retrieve(expanded)

    def _threshold_fallback(self, own_violations: list[ThresholdViolation]) -> dict:
        """
        Pure threshold-based result used when the LLM is unavailable (e.g. rate-limited).
        Derives disposition, root cause and corrective actions from violations alone so that
        no LLM error details are ever exposed in the user-facing report.
        """
        if not own_violations:
            return {
                "disposition": "PASS",
                "defect_categories": [],
                "root_cause": "No threshold violations detected in monitored features.",
                "corrective_actions": [],
                "standards_references": [],
            }

        risk_viols = [v for v in own_violations if v.severity == "RISK"]
        marginal_viols = [v for v in own_violations if v.severity == "MARGINAL"]

        if risk_viols:
            disposition = "REWORK_REQUIRED"
        elif marginal_viols:
            disposition = "CONDITIONAL"
        else:
            disposition = "PASS"

        # Defect categories — deduplicated, order-preserving
        seen: set[str] = set()
        defect_categories: list[str] = []
        for v in own_violations:
            for cat in v.defect_categories:
                if cat not in seen:
                    seen.add(cat)
                    defect_categories.append(cat)

        # Root cause — describe violations without any LLM error text
        if risk_viols:
            feat_list = ", ".join(v.feature.replace("_", " ") for v in risk_viols)
            root_cause = (
                f"RISK-level exceedance in: {feat_list}. "
                f"Threshold violations indicate elevated defect probability."
            )
        else:
            feat_list = ", ".join(v.feature.replace("_", " ") for v in marginal_viols)
            root_cause = (
                f"Marginal values in: {feat_list}. "
                f"Monitor closely and review process parameters."
            )

        # Corrective actions — one per violation, deterministic
        corrective_actions: list[str] = []
        for v in own_violations:
            direction = "below" if v.threshold_type == "max" else "above"
            unit_str = f" {v.unit}" if v.unit else ""
            label = _FEATURE_LABELS.get(v.feature, v.feature.replace("_", " "))
            corrective_actions.append(
                f"Adjust {label} {direction} "
                f"{v.threshold}{unit_str} (current: {v.value:.3g}{unit_str})"
            )

        return {
            "disposition": disposition,
            "defect_categories": defect_categories,
            "root_cause": root_cause,
            "corrective_actions": corrective_actions[:4],
            "standards_references": [],
        }

    def _call_llm(self, prompt: str) -> tuple[dict, str, bool]:
        """Returns (parsed_dict, raw_str, fallback_used).

        parsed_dict is empty ({}) when the LLM call fails with an API error
        (e.g. rate-limit 429, network error). run() detects the empty dict and
        calls _threshold_fallback() so no error text reaches the user-facing report.
        """
        raw = ""
        version = PROMPT_VERSIONS.get(self.agent_name, "unknown")
        logger.info(
            "llm_call_start",
            extra={"agent_name": self.agent_name, "prompt_version": version},
        )
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
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    parsed = {}
            else:
                parsed = {}
            fallback_used = True
        except Exception as e:
            # Log for ops visibility; return empty dict so run() uses threshold fallback.
            # Never put the raw exception in the returned dict — it would reach the user report.
            logger.warning(
                "[%s] LLM call failed (%s): %s — threshold-based fallback will be used",
                self.agent_name,
                type(e).__name__,
                e,
            )
            parsed = {}
            fallback_used = True
        return parsed, raw, fallback_used

    def run(
        self,
        prediction: WeldPrediction,
        features: SessionFeatures,
        violations: list[ThresholdViolation],
    ) -> SpecialistResult:
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
        chunks = self._retrieve(queries, own_violations)
        prompt = self._build_prompt(prediction, features, own_violations, chunks)
        parsed, raw, fallback_used = self._call_llm(prompt)
        if fallback_used and not parsed:
            # LLM API unavailable (e.g. rate-limited) — derive result from violations only.
            parsed = self._threshold_fallback(own_violations)

        disposition = parsed.get("disposition", "CONDITIONAL")
        lof_lop_risk = any(
            v.severity == "RISK"
            and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in own_violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"

        self._log(
            f"  [{self.agent_name}] {disposition} — triggered: {triggered_features}"
        )

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
    OWNED_FEATURES = {
        "heat_diss_max_spike",
        "heat_input_min_rolling",
        "heat_input_drop_severity",
    }
    # heat_diss_mean: context-only in prompts, no threshold band — excluded from OWNED_FEATURES

    @property
    def agent_name(self) -> str:
        return "ThermalAgent"

    @property
    def domain(self) -> str:
        return "thermal"

    def _get_triggered_features(self, features: SessionFeatures) -> list[str]:
        fv = features.to_vector()
        t = THRESHOLDS
        out = []
        if fv.get("heat_diss_max_spike", 0) > t["heat_diss_max_spike"]["good_max"]:
            out.append("heat_diss_max_spike")
        if (
            fv.get("heat_input_min_rolling", float("inf"))
            < t["heat_input_min_rolling"]["good_min"]
        ):
            out.append("heat_input_min_rolling")
        if (
            fv.get("heat_input_drop_severity", 0)
            > t["heat_input_drop_severity"]["good_max"]
        ):
            out.append("heat_input_drop_severity")
        return out

    def _get_queries(self, prediction, features, violations) -> list[str]:
        queries = [
            "heat dissipation spike thermal instability corrective travel speed preheat",
            "cold arc window heat input minimum rolling incomplete penetration LOF LOP",
        ]
        if any(v.feature == "heat_input_drop_severity" for v in violations):
            queries.append(
                "stitch welding restart heat drop severity corrective action"
            )
        if any(v.severity == "RISK" for v in violations):
            queries.append(
                "REWORK_REQUIRED thermal LOF LOP ISO 5817 acceptance criteria"
            )
        return queries

    def _build_prompt(self, prediction, features, violations, chunks) -> str:
        fv = features.to_vector()
        violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
        context = "\n\n".join(
            f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}" for c in chunks
        )
        thermal_vals = "\n".join(
            f"  {f}: {fv.get(f, 'N/A')}"
            for f in [
                "heat_diss_max_spike",
                "heat_diss_mean",
                "heat_input_min_rolling",
                "heat_input_drop_severity",
            ]
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

    @property
    def domain(self) -> str:
        return "geometry"

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
            queries.append(
                "angle deviation REWORK LOF ISO 5817 acceptance criteria repair"
            )
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
    OWNED_FEATURES = {
        "voltage_cv",
        "amps_cv",
        "heat_input_cv",
        "arc_on_ratio",
        "heat_input_mean",
    }

    @property
    def agent_name(self) -> str:
        return "ProcessStabilityAgent"

    @property
    def domain(self) -> str:
        return "process"

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
        if any(
            v.feature in {"heat_input_cv", "amps_cv", "heat_input_mean"}
            for v in violations
        ):
            queries.append(
                "heat input CV amps mean process parameter corrective WPS bounds"
            )
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
            for f in [
                "voltage_cv",
                "amps_cv",
                "heat_input_cv",
                "arc_on_ratio",
                "heat_input_mean",
            ]
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
            v.severity == "RISK"
            and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
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
            rework_agents = [
                r.agent_name for r in active if r.disposition == "REWORK_REQUIRED"
            ]
            active_names = [r.agent_name for r in active]
            if rework_agents:
                rationale = f"{', '.join(rework_agents)} flagged REWORK_REQUIRED. Safety override applied."
            elif disposition == "CONDITIONAL":
                rationale = (
                    f"{', '.join(active_names)}: CONDITIONAL. Monitor next 3 sessions."
                )
            else:
                rationale = (
                    f"All active specialists ({', '.join(active_names)}) returned PASS."
                )
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
