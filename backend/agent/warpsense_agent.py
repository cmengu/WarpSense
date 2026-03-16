"""
WarpSense — Quality Assessment Agent
backend/agent/warpsense_agent.py

6-step deterministic pipeline. No skipping, no reordering.
Consumes WeldPrediction + SessionFeatures from Phase 1.
Retrieves welding standards from ChromaDB.
Calls Groq LLM to generate a structured quality report.
Self-checks that every standards citation is grounded in retrieved content.
Returns WeldQualityReport.

Step ordering is a safety property, not a preference:
  1. Defect intake   — map top_drivers -> defect categories
  2. Threshold check — quantify which features exceed safe ranges
  3. Standards pull  — retrieve grounding from ChromaDB (AWS D1.1 / ISO 5817 / IACS)
  4. LLM generation  — structured prompt -> quality report fields
  5. Self-check      — verify every citation exists in retrieved content
  6. Return report   — WeldQualityReport dataclass

Usage:
    from backend.agent.warpsense_agent import WarpSenseAgent
    agent = WarpSenseAgent()
    report = agent.assess(prediction, features)
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from groq import Groq
import chromadb
from chromadb.utils import embedding_functions

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_KB_PATH = _HERE.parent / "knowledge" / "chroma_db"

THRESHOLDS = {
    "heat_diss_max_spike": {
        "good_max": 10.0,
        "marginal_max": 40.0,
        "unit": "C/s",
        "defect_map": ["LOF", "POROSITY"],
        "direction": "high_is_bad",
    },
    "angle_deviation_mean": {
        "good_max": 8.0,
        "marginal_max": 15.0,
        "unit": "deg",
        "defect_map": ["LOF", "UNDERCUT"],
        "direction": "high_is_bad",
    },
    "heat_input_min_rolling": {
        "good_min": 4000.0,
        "marginal_min": 3500.0,
        "unit": "J",
        "defect_map": ["LOF", "LOP"],
        "direction": "low_is_bad",
    },
    "heat_input_drop_severity": {
        "good_max": 10.0,
        "marginal_max": 15.0,
        "unit": "",
        "defect_map": ["LOF"],
        "direction": "high_is_bad",
    },
    "heat_input_cv": {
        "good_max": 0.10,
        "marginal_max": 0.20,
        "unit": "",
        "defect_map": ["LOF", "LOP"],
        "direction": "high_is_bad",
    },
    "voltage_cv": {
        "good_max": 0.08,
        "marginal_max": 0.15,
        "unit": "",
        "defect_map": ["POROSITY"],
        "direction": "high_is_bad",
    },
    "amps_cv": {
        "good_max": 0.08,
        "marginal_max": 0.12,
        "unit": "",
        "defect_map": ["LOF", "LOP"],
        "direction": "high_is_bad",
    },
    "arc_on_ratio": {
        "good_min": 0.90,
        "marginal_min": 0.75,
        "unit": "",
        "defect_map": ["LOF"],
        "direction": "low_is_bad",
    },
    "angle_max_drift_1s": {
        "good_max": 10.0,
        "marginal_max": 15.0,
        "unit": "deg",
        "defect_map": ["LOF"],
        "direction": "high_is_bad",
    },
    "heat_input_mean": {
        "good_min": 4500.0,
        "marginal_min": 3800.0,
        "unit": "J",
        "defect_map": ["LOF", "LOP"],
        "direction": "low_is_bad",
    },
}

DEFECT_FULL_NAME = {
    "LOF": "LACK OF FUSION (ISO 6520-1: 401)",
    "LOP": "INCOMPLETE ROOT PENETRATION (ISO 6520-1: 4021)",
    "POROSITY": "POROSITY (ISO 6520-1: 2017)",
    "UNDERCUT": "UNDERCUT (ISO 6520-1: 5011)",
    "THERMAL_INSTABILITY": "THERMAL INSTABILITY",
}

LOF_LOP_PRIMARY_FEATURES = {
    "heat_diss_max_spike",
    "angle_deviation_mean",
    "heat_input_min_rolling",
    "heat_input_drop_severity",
}

LLM_MODEL = "llama-3.3-70b-versatile"


@dataclass
class ThresholdViolation:
    feature: str
    value: float
    threshold: float
    threshold_type: str
    severity: str
    unit: str
    defect_categories: list

    def as_display_line(self) -> str:
        direction = ">" if self.threshold_type == "max" else "<"
        unit = f" {self.unit}" if self.unit else ""
        return (
            f"  * {self.feature:<28} {self.value:.3f}{unit}  "
            f"(threshold: {direction} {self.threshold:.3f}{unit})  "
            f"[{self.severity}] -> {', '.join(self.defect_categories)}"
        )


@dataclass
class StandardsChunk:
    chunk_id: str
    text: str
    source: str
    section: str
    score: float


@dataclass
class WeldQualityReport:
    session_id: str
    report_timestamp: str
    quality_class: str
    confidence: float
    iso_5817_level: str
    primary_defect_categories: list
    threshold_violations: list
    root_cause: str
    corrective_actions: list
    standards_references: list
    retrieved_chunks_used: list
    disposition: str
    disposition_rationale: str
    self_check_passed: bool
    self_check_notes: str
    llm_raw_response: str

    def render(self) -> str:
        return _render_report(self)


def _render_report(r) -> str:
    disposition_icon = {"PASS": "[PASS]", "CONDITIONAL": "[CONDITIONAL]", "REWORK_REQUIRED": "[REWORK]"}.get(r.disposition, "[?]")
    quality_icon = {"GOOD": "[GOOD]", "MARGINAL": "[MARGINAL]", "DEFECTIVE": "[DEFECTIVE]"}.get(r.quality_class, "[?]")
    lines = [
        "=" * 58,
        f"WARPSENSE QUALITY REPORT -- WELD SESSION {r.session_id}",
        "=" * 58,
        f"Quality Class:      {quality_icon} {r.quality_class}",
        f"ISO 5817 Level:     {r.iso_5817_level}",
        f"Confidence:         {r.confidence:.2f}",
        f"Report Time:        {r.report_timestamp}",
        "",
    ]
    if r.threshold_violations:
        lines.append("Threshold Violations:")
        for v in r.threshold_violations:
            lines.append(v.as_display_line())
        lines.append("")
    if r.primary_defect_categories:
        lines.append("Primary Defect Risk Categories:")
        for cat in r.primary_defect_categories:
            lines.append(f"  * {DEFECT_FULL_NAME.get(cat, cat)}")
        lines.append("")
    lines.append("Root Cause:")
    for line in r.root_cause.strip().splitlines():
        lines.append(f"  {line.strip()}")
    lines.append("")
    if r.corrective_actions:
        lines.append("Corrective Parameters:")
        for action in r.corrective_actions:
            lines.append(f"  -> {action}")
        lines.append("")
    if r.standards_references:
        lines.append("Standards References:")
        for ref in r.standards_references:
            lines.append(f"  * {ref}")
        lines.append("")
    check = "PASSED" if r.self_check_passed else "FLAGGED"
    lines.append(f"Self-Check:         {check}")
    if not r.self_check_passed:
        lines.append(f"  Note: {r.self_check_notes}")
    lines.append("")
    lines.append(f"Disposition:        {disposition_icon} {r.disposition.replace('_', ' ')}")
    lines.append(f"  {r.disposition_rationale}")
    lines.append("=" * 58)
    return "\n".join(lines)


class WarpSenseAgent:
    """6-step deterministic welding quality assessment agent."""

    def __init__(
        self,
        chroma_path=None,
        collection_name="welding_standards",
        llm_model=LLM_MODEL,
        n_standards_chunks=6,
        verbose=True,
    ):
        self.llm_model = llm_model
        self.n_chunks = n_standards_chunks
        self.verbose = verbose

        # Groq client -- reads GROQ_API_KEY from env
        self.groq = Groq()

        kb_path = chroma_path or str(_KB_PATH)
        self._log(f"[Agent] Loading ChromaDB from: {kb_path}")
        client = chromadb.PersistentClient(path=kb_path)
        ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = client.get_collection(
            name=collection_name,
            embedding_function=ef,
        )
        self._log(f"[Agent] KB loaded: {self.collection.count()} chunks")

    # Stable public wrappers used by eval_prompts.py.
    # These keep eval code decoupled from private step method names.
    def prepare_context(self, features: "SessionFeatures", prediction: "WeldPrediction") -> tuple:
        """
        Run Steps 1–3 and return (violations, chunks, defect_categories).

        Note: prepare_context takes (features, prediction) but
        _step3_retrieve_standards takes (prediction, features, ...).
        The argument order reversal is intentional.
        """
        defect_categories = self._step1_defect_intake(prediction, features)
        violations = self._step2_threshold_check(features)
        chunks = self._step3_retrieve_standards(
            prediction, features, defect_categories, violations
        )
        return violations, chunks, defect_categories

    def verify_citations(self, report_dict: dict, chunks: list) -> tuple:
        """
        Run citation grounding check and return (passed, reason).
        """
        return self._step5_self_check(report_dict, chunks)

    def assess(self, prediction, features):
        session_id = prediction.session_id
        self._log(f"\n[Agent] -- Starting assessment: {session_id} --")
        self._log("[Agent] Step 1: Defect intake")
        defect_categories = self._step1_defect_intake(prediction, features)
        self._log("[Agent] Step 2: Threshold check")
        violations = self._step2_threshold_check(features)
        self._log("[Agent] Step 3: Standards retrieval")
        chunks = self._step3_retrieve_standards(prediction, features, defect_categories, violations)
        self._log("[Agent] Step 4: LLM generation")
        llm_output = self._step4_llm_generate(prediction, features, defect_categories, violations, chunks)
        self._log("[Agent] Step 5: Self-check")
        self_check_passed, self_check_notes = self._step5_self_check(llm_output, chunks)
        self._log("[Agent] Step 6: Assembling report")
        report = self._step6_assemble_report(
            prediction, features, defect_categories, violations,
            chunks, llm_output, self_check_passed, self_check_notes
        )
        self._log(f"[Agent] -- Assessment complete: {report.disposition} --\n")
        return report

    def _step1_defect_intake(self, prediction, features):
        defects = set()
        feat_dict = features.to_vector()
        driver_feature_to_defect = {
            "heat_diss_max_spike":      ["LOF", "POROSITY"],
            "angle_deviation_mean":     ["LOF", "UNDERCUT"],
            "heat_input_min_rolling":   ["LOF", "LOP"],
            "heat_input_drop_severity": ["LOF"],
            "heat_input_cv":            ["LOF", "LOP"],
            "amps_cv":                  ["LOF", "LOP"],
            "voltage_cv":               ["POROSITY"],
            "arc_on_ratio":             ["LOF"],
            "heat_input_mean":          ["LOF", "LOP"],
            "angle_max_drift_1s":       ["LOF"],
            "heat_diss_mean":           ["LOF"],
        }
        for feat_name, _ in prediction.top_drivers:
            for cat in driver_feature_to_defect.get(feat_name, []):
                defects.add(cat)
        for feat_name in LOF_LOP_PRIMARY_FEATURES:
            val = feat_dict.get(feat_name)
            if val is None:
                continue
            t = THRESHOLDS.get(feat_name, {})
            if t.get("direction") == "high_is_bad":
                if val > t.get("marginal_max", float("inf")):
                    for cat in t.get("defect_map", []):
                        defects.add(cat)
            elif t.get("direction") == "low_is_bad":
                if val < t.get("marginal_min", 0.0):
                    for cat in t.get("defect_map", []):
                        defects.add(cat)
        hd = feat_dict.get("heat_diss_max_spike", 0)
        if hd > THRESHOLDS["heat_diss_max_spike"]["good_max"]:
            defects.add("THERMAL_INSTABILITY")
        ordered = []
        for cat in ["LOF", "LOP", "THERMAL_INSTABILITY", "UNDERCUT", "POROSITY"]:
            if cat in defects:
                ordered.append(cat)
        self._log(f"  -> Defect categories: {ordered}")
        return ordered

    def _step2_threshold_check(self, features):
        feat_dict = features.to_vector()
        violations = []
        for feat_name, t in THRESHOLDS.items():
            val = feat_dict.get(feat_name)
            if val is None:
                continue
            severity = None
            threshold_val = None
            threshold_type = None
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
        self._log(f"  -> {len(violations)} violations: "
                  f"{sum(1 for v in violations if v.severity=='RISK')} RISK, "
                  f"{sum(1 for v in violations if v.severity=='MARGINAL')} MARGINAL")
        return violations

    def _step3_retrieve_standards(self, prediction, features, defect_categories, violations):
        queries = []
        cat_queries = {
            "LOF":                "lack of fusion incomplete fusion acceptance criteria corrective action",
            "LOP":                "incomplete root penetration corrective action acceptance criteria",
            "THERMAL_INSTABILITY":"heat dissipation spike thermal instability corrective travel speed",
            "UNDERCUT":           "undercut acceptance criteria corrective action torch angle current",
            "POROSITY":           "porosity root cause corrective action shielding gas heat dissipation",
        }
        for cat in defect_categories[:3]:
            q = cat_queries.get(cat)
            if q:
                queries.append(q)
        for v in violations[:2]:
            queries.append(f"{v.feature.replace('_', ' ')} {v.value:.1f} corrective action threshold")
        queries.append("marine shipyard LOF LOP sensor detection invisible inspection")
        seen = set()
        unique_queries = [q for q in queries if not (q in seen or seen.add(q))]
        seen_ids = set()
        all_chunks = []
        for q in unique_queries[:5]:
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
                        all_chunks.append(StandardsChunk(
                            chunk_id=chunk_id, text=doc,
                            source=meta.get("source", "unknown"),
                            section=meta.get("section", ""),
                            score=round(1 - results["distances"][0][i], 4),
                        ))
            except Exception as e:
                self._log(f"  [WARN] KB query failed: {e}")
        all_chunks.sort(key=lambda c: c.score, reverse=True)
        top_chunks = all_chunks[:self.n_chunks]
        if top_chunks:
            self._log(f"  -> Retrieved {len(top_chunks)} chunks (top score: {top_chunks[0].score:.4f} from {top_chunks[0].source})")
        return top_chunks

    def _step4_llm_generate(self, prediction, features, defect_categories, violations, chunks):
        feat_dict = features.to_vector()
        violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
        defects_text = ", ".join(defect_categories) or "None identified"
        top_drivers_text = "\n".join(
            f"  {name}: importance={imp:.3f}" for name, imp in prediction.top_drivers
        )
        chunks_text = "\n\n".join(
            f"[CHUNK {i+1}] Source: {c.source} | {c.section}\n{c.text}"
            for i, c in enumerate(chunks)
        )
        feature_summary = "\n".join(f"  {k}: {v:.4f}" for k, v in feat_dict.items())

        prompt = f"""You are WarpSenseAgent, an industrial welding quality assessment AI.

CLASSIFIER OUTPUT
Session ID: {prediction.session_id}
Quality Class: {prediction.quality_class}
Confidence: {prediction.confidence:.2f}
Top Feature Drivers:
{top_drivers_text}

SESSION FEATURES
{feature_summary}

THRESHOLD VIOLATIONS
{violations_text}

DEFECT RISK CATEGORIES
{defects_text}

RETRIEVED WELDING STANDARDS
{chunks_text}

INSTRUCTIONS
Produce a structured JSON report with EXACTLY these keys:
{{
"iso_5817_level": "B" | "C" | "D" | "BELOW_D",
"disposition": "PASS" | "CONDITIONAL" | "REWORK_REQUIRED",
"disposition_rationale": "One sentence.",
"root_cause": "2-4 sentences linking sensor features to defect mechanism.",
"corrective_actions": ["Action 1", "Action 2", "Action 3"],
"standards_references": ["Standard 1: source + section + relevance"]
}}
RULES:
1. iso_5817_level: GOOD->C or B, MARGINAL->D, DEFECTIVE->BELOW_D.
2. disposition must be REWORK_REQUIRED if quality_class is DEFECTIVE or any LOF/LOP feature is RISK.
3. corrective_actions within WPS bounds: amperage +/-15%, voltage +/-10%, travel speed +/-30%, angle +/-10% of 45deg.
4. Every standards_reference must come ONLY from retrieved chunks above.
5. 3-5 corrective_actions.
6. Respond with ONLY the JSON object. No preamble, no markdown fences."""

        response = self.groq.chat.completions.create(
            model=self.llm_model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()

        clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            self._log(f"  [WARN] LLM JSON parse failed: {e}. Using fallback.")
            parsed = self._fallback_report(prediction, defect_categories, violations)
            parsed["_parse_error"] = str(e)

        parsed["_raw"] = raw
        return parsed

    def _fallback_report(self, prediction, defect_categories, violations):
        has_risk = any(v.severity == "RISK" for v in violations)
        lof_risk = any(v.feature in LOF_LOP_PRIMARY_FEATURES for v in violations if v.severity == "RISK")
        return {
            "iso_5817_level": "BELOW_D" if prediction.quality_class == "DEFECTIVE" else "D",
            "disposition": "REWORK_REQUIRED" if lof_risk else ("CONDITIONAL" if has_risk else "PASS"),
            "disposition_rationale": f"Classification: {prediction.quality_class} with {len(violations)} violations.",
            "root_cause": "LLM generation failed. Review threshold violations directly.",
            "corrective_actions": ["Review threshold violations above", "Consult welding engineer"],
            "standards_references": [],
        }

    def _step5_self_check(self, llm_output, chunks):
        cited_refs = llm_output.get("standards_references", [])
        if not cited_refs:
            return True, "No citations to verify."
        known_sources = set()
        for c in chunks:
            src = c.source.lower()
            known_sources.add(src)
            if "aws" in src:
                known_sources.update(["aws d1.1", "aws"])
            if "iso 5817" in src:
                known_sources.add("iso 5817")
            if "iacs" in src:
                known_sources.update(["iacs", "iacs rec"])
            if "iso 6520" in src:
                known_sources.add("iso 6520")
        hallucinated = []
        for ref in cited_refs:
            ref_lower = ref.lower()
            grounded = any(src in ref_lower for src in known_sources)
            if not grounded:
                section_match = any(
                    any(token in c.text.lower() for token in ref_lower.split() if len(token) > 4)
                    for c in chunks
                )
                if not section_match:
                    hallucinated.append(ref)
        if hallucinated:
            notes = f"Ungrounded citations: {hallucinated}"
            self._log(f"  [SELF-CHECK] WARNING: {notes}")
            return False, notes
        self._log("  [SELF-CHECK] All citations grounded.")
        return True, "All citations verified."

    def _step6_assemble_report(self, prediction, features, defect_categories, violations, chunks, llm_output, self_check_passed, self_check_notes):
        disposition = llm_output.get("disposition", "CONDITIONAL")
        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"
            llm_output["disposition_rationale"] = (
                "[Override] LOF/LOP RISK threshold exceeded. "
                + llm_output.get("disposition_rationale", "")
            )
        return WeldQualityReport(
            session_id=prediction.session_id,
            report_timestamp=datetime.now(timezone.utc).isoformat(),
            quality_class=prediction.quality_class,
            confidence=prediction.confidence,
            iso_5817_level=llm_output.get("iso_5817_level", "D"),
            primary_defect_categories=defect_categories,
            threshold_violations=violations,
            root_cause=llm_output.get("root_cause", ""),
            corrective_actions=llm_output.get("corrective_actions", []),
            standards_references=llm_output.get("standards_references", []),
            retrieved_chunks_used=[c.chunk_id for c in chunks],
            disposition=disposition,
            disposition_rationale=llm_output.get("disposition_rationale", ""),
            self_check_passed=self_check_passed,
            self_check_notes=self_check_notes,
            llm_raw_response=llm_output.get("_raw", ""),
        )

    def _log(self, msg):
        if self.verbose:
            print(msg)