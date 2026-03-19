"""
warpsense_langchain_agent.py
-----------------------------
LangChain tool-calling comparison agent for WarpSense.

Exposes the same .assess(prediction, features) -> WeldQualityReport interface
as WarpSenseAgent and WarpSenseGraph (Liskov Substitution).

Tools:
  retrieve_standards(query)          — queries ChromaDB for welding standards
  get_domain_context(domain)         — returns feature values and violations for a domain

Known limitation: primary_defect_categories is always [] in reports from this agent.
Metrics that use defect categories will show this agent performing worse than actual.
FNR/F1 comparison is unaffected.

Usage:
    from agent.warpsense_langchain_agent import WarpSenseLangChainAgent
    agent = WarpSenseLangChainAgent()
    report = agent.assess(prediction, features)  # → WeldQualityReport
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "chroma_db"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chromadb
from chromadb.utils import embedding_functions
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from agent.warpsense_agent import LLM_MODEL, WeldQualityReport, ThresholdViolation
from agent.specialists import (
    compute_violations,
    thermal_triggered,
    geometry_triggered,
    process_triggered,
)
from features.session_feature_extractor import SessionFeatures, OPTIMAL_ANGLE_DEG
from features.weld_classifier import WeldPrediction

import logging

logger = logging.getLogger(__name__)


class WarpSenseLangChainAgent:
    """
    LangChain tool-calling agent. Single-threaded only — session_ref is an instance attribute;
    concurrent assess() calls on the same instance would race.
    For parallel eval, replace self._session with contextvars.ContextVar.
    """

    def __init__(
        self,
        chroma_path=None,
        chroma_client: Optional[chromadb.PersistentClient] = None,
        collection_name: str = "welding_standards",
        llm_model: str = LLM_MODEL,
        verbose: bool = True,
    ):
        self.verbose = verbose
        self.llm_model = llm_model

        # If chroma_client provided (eval_multi_agent), use it. Else create own.
        if chroma_client is not None:
            client = chroma_client
        else:
            kb_path = chroma_path or str(_KB_PATH)
            client = chromadb.PersistentClient(path=kb_path)
        ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = client.get_collection(name=collection_name, embedding_function=ef)

        self._llm = ChatGroq(
            model=llm_model,
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=0.1,
            max_tokens=800,
        )

        # session_ref holds current session context for tool closures (single-threaded)
        self._session: Optional[dict] = None

        self._tools = self._build_tools()
        self._agent_executor = self._build_executor()

    def _log(self, msg: str) -> None:
        if self.verbose:
            logger.info(msg)

    def _build_tools(self):
        agent_self = self

        @tool
        def retrieve_standards(query: str) -> str:
            """
            Query the welding standards knowledge base for relevant standards, guidelines, and acceptance criteria.
            Use targeted queries about specific defects, features, or standards (e.g. 'LOF ISO 5817 repair criteria').
            """
            try:
                results = agent_self._collection.query(
                    query_texts=[query],
                    n_results=4,
                    include=["documents", "metadatas", "distances"],
                )
                chunks = []
                for i, doc in enumerate(results["documents"][0]):
                    chunk_id = results["ids"][0][i]
                    meta = results["metadatas"][0][i]
                    source = meta.get("source", "unknown")
                    section = meta.get("section", "")
                    chunks.append(f"[{chunk_id}] {source} | {section}\n{doc}")
                return "\n\n".join(chunks)
            except Exception as e:
                return f"Retrieval failed: {e}"

        @tool
        def get_domain_context(domain: Literal["thermal", "geometry", "process"]) -> str:
            """
            Get feature values and violations for the specified domain.
            domain: 'thermal' | 'geometry' | 'process'. Call get_domain_context(domain='thermal'),
            get_domain_context(domain='geometry'), get_domain_context(domain='process') for each domain
            present in the session violations.
            """
            session = agent_self._session
            if not session:
                return "No session loaded."
            features = session["features"]
            violations = session["violations"]
            fv = features.to_vector()
            angle_note = ""
            if domain == "thermal":
                feats = ["heat_diss_max_spike", "heat_diss_mean", "heat_input_min_rolling", "heat_input_drop_severity"]
                triggered = thermal_triggered(features)
            elif domain == "geometry":
                feats = ["angle_deviation_mean", "angle_max_drift_1s"]
                triggered = geometry_triggered(features)
                angle_note = (
                    f"Target angle: {OPTIMAL_ANGLE_DEG:.0f}° (not 45°). "
                    f"angle_deviation_mean = |measured - {OPTIMAL_ANGLE_DEG:.0f}|. "
                    f"Correct to {OPTIMAL_ANGLE_DEG:.0f} ± 5 degrees."
                )
            else:
                feats = ["voltage_cv", "amps_cv", "heat_input_cv", "arc_on_ratio", "heat_input_mean"]
                triggered = process_triggered(features)
            domain_feats = {f: fv.get(f) for f in feats}
            domain_viols = [v for v in violations if v.feature in domain_feats]
            viol_text = "\n".join(v.as_display_line() for v in domain_viols) or "None"
            feat_text = "\n".join(f"  {k}: {val}" for k, val in domain_feats.items())
            note_line = f"\nNote: {angle_note}" if angle_note else ""
            return (
                f"{domain.capitalize()} triggered: {triggered}\n"
                f"{domain.capitalize()} Features:\n{feat_text}\n"
                f"{domain.capitalize()} Violations:\n{viol_text}"
                f"{note_line}"
            )

        return [retrieve_standards, get_domain_context]

    def _build_executor(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages([
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
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self._llm, self._tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=self.verbose,
            handle_parsing_errors=True,
            max_iterations=10,
        )

    def _parse_output(self, raw_output: str, prediction: WeldPrediction, violations: list[ThresholdViolation]) -> WeldQualityReport:
        """Parse LLM JSON output into WeldQualityReport. Applies LOF/LOP safety override."""
        parsed = {}
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", raw_output, flags=re.MULTILINE)
            clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
            parsed = json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except (json.JSONDecodeError, TypeError):
                    parsed = {}

        if not parsed:
            return self._fallback_report(prediction, violations, "LLM output unparseable")

        disposition = parsed.get("disposition", "CONDITIONAL")

        # LOF/LOP safety override: any RISK violation in LOF/LOP features → REWORK_REQUIRED
        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in violations
        )
        if lof_lop_risk and disposition != "REWORK_REQUIRED":
            disposition = "REWORK_REQUIRED"

        iso_map = {"DEFECTIVE": "BELOW_D", "MARGINAL": "D", "GOOD": "C"}
        iso_5817_level = parsed.get("iso_5817_level", iso_map.get(prediction.quality_class, "D"))

        return WeldQualityReport(
            session_id=prediction.session_id,
            report_timestamp=datetime.now(timezone.utc).isoformat(),
            quality_class=prediction.quality_class,
            confidence=prediction.confidence,
            iso_5817_level=iso_5817_level,
            primary_defect_categories=[],  # LangChain comparison: hardcoded — known limitation
            threshold_violations=violations,
            root_cause=parsed.get("root_cause", "LLM output could not be parsed."),
            corrective_actions=parsed.get("corrective_actions", []),
            standards_references=parsed.get("standards_references", []),
            retrieved_chunks_used=[],
            disposition=disposition,
            disposition_rationale=parsed.get("disposition_rationale", f"{disposition} per LangChain agent."),
            self_check_passed=False,
            self_check_notes="LangChain: no citation cross-check performed.",
            llm_raw_response=raw_output,
        )

    def _fallback_report(self, prediction: WeldPrediction, violations: list[ThresholdViolation], error: str) -> WeldQualityReport:
        """Deterministic fallback when LLM/agent fails. Applies safety override on LOF/LOP RISK."""
        lof_lop_risk = any(
            v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
            for v in violations
        )
        disposition = "REWORK_REQUIRED" if lof_lop_risk else "CONDITIONAL"
        iso_map = {"DEFECTIVE": "BELOW_D", "MARGINAL": "D", "GOOD": "C"}
        return WeldQualityReport(
            session_id=prediction.session_id,
            report_timestamp=datetime.now(timezone.utc).isoformat(),
            quality_class=prediction.quality_class,
            confidence=prediction.confidence,
            iso_5817_level=iso_map.get(prediction.quality_class, "D"),
            primary_defect_categories=[],
            threshold_violations=violations,
            root_cause=f"LangChain agent failed: {error}",
            corrective_actions=["Review threshold violations. Manual inspection required."],
            standards_references=[],
            retrieved_chunks_used=[],
            disposition=disposition,
            disposition_rationale=f"Fallback: LangChain agent error. LOF/LOP safety override={'yes' if lof_lop_risk else 'no'}.",
            self_check_passed=False,
            self_check_notes=f"Agent execution failed: {error}",
            llm_raw_response="",
        )

    def assess(self, prediction: WeldPrediction, features: SessionFeatures) -> WeldQualityReport:
        violations = compute_violations(features)

        # Load session context for tool closures (single-threaded)
        self._session = {"features": features, "violations": violations}

        try:
            session_summary = (
                f"Session: {prediction.session_id} | Class: {prediction.quality_class} ({prediction.confidence:.2f})\n"
                f"Violations: {len(violations)} total\n"
                + "\n".join(v.as_display_line() for v in violations[:5])
                + (f"\n... and {len(violations) - 5} more" if len(violations) > 5 else "")
            )
            result = self._agent_executor.invoke({"input": session_summary})
            raw_output = result.get("output", "")
            self._log(f"[LangChain] Raw output: {raw_output[:200]}...")
            report = self._parse_output(raw_output, prediction, violations)
        except Exception as e:
            self._log(f"[LangChain] Agent failed: {e}")
            report = self._fallback_report(prediction, violations, str(e))
        finally:
            self._session = None

        self._log(f"[LangChain] {report.disposition} for {prediction.session_id}")
        return report
