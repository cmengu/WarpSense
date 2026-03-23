"""
warpsense_graph.py
------------------
LangGraph orchestrator for the WarpSense multi-agent pipeline.

Graph architecture (sequential, deterministic):
  route_node → thermal_node → geometry_node → process_node → summary_node

Each specialist self-determines via _get_triggered_features() — specialist nodes do NOT
read routing_decision. The routing_decision field in WarpSenseState is for observability
and logging only.

Usage:
    from agent.warpsense_graph import WarpSenseGraph
    graph = WarpSenseGraph()
    report = graph.assess(prediction, features)  # → WeldQualityReport
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, TypedDict

_ROOT = Path(__file__).resolve().parent.parent.parent
_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "chroma_db"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chromadb
from groq import Groq

import logging

logger = logging.getLogger(__name__)

from agent.warpsense_agent import LLM_MODEL, WeldQualityReport
from agent.specialists import ThresholdViolation
from agent.specialists import (
    SpecialistResult,
    ThermalAgent,
    GeometryAgent,
    ProcessStabilityAgent,
    SummaryAgent,
    compute_violations,
    thermal_triggered,
    geometry_triggered,
    process_triggered,
)
from knowledge.rag_retriever import RAGRetriever
from features.session_feature_extractor import SessionFeatures
from features.weld_classifier import WeldPrediction


class WarpSenseState(TypedDict):
    session_id: str
    features: SessionFeatures
    prediction: WeldPrediction
    violations: list[ThresholdViolation]
    routing_decision: Dict[
        str, bool
    ]  # thermal_triggered, geometry_triggered, process_triggered — observability only
    thermal_result: Optional[SpecialistResult]
    geometry_result: Optional[SpecialistResult]
    process_result: Optional[SpecialistResult]
    final_report: Optional[WeldQualityReport]


class WarpSenseGraph:
    """
    LangGraph coordinator. Exposes .assess(prediction, features) -> WeldQualityReport
    to match the WarpSenseAgent interface (Liskov Substitution).
    """

    def __init__(
        self,
        chroma_path=None,
        chroma_client: Optional[chromadb.PersistentClient] = None,
        collection_name: str = "welding_standards",
        llm_model: str = LLM_MODEL,
        n_chunks_per_specialist: int = 4,
        verbose: bool = True,
    ):
        self.verbose = verbose

        # If chroma_client provided (eval_multi_agent), use it. Else create own.
        if chroma_client is not None:
            client = chroma_client
        else:
            kb_path = chroma_path or str(_KB_PATH)
            client = chromadb.PersistentClient(path=kb_path)
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        retriever = RAGRetriever(
            chroma_client=client,
            collection_name=collection_name,
            n_results=n_chunks_per_specialist,
        )
        self._thermal = ThermalAgent(
            groq_client, retriever, llm_model, n_chunks_per_specialist, verbose
        )
        self._geometry = GeometryAgent(
            groq_client, retriever, llm_model, n_chunks_per_specialist, verbose
        )
        self._process = ProcessStabilityAgent(
            groq_client, retriever, llm_model, n_chunks_per_specialist, verbose
        )
        self._summary = SummaryAgent()

        self._graph = self._build_graph()

    def _log(self, msg: str) -> None:
        if self.verbose:
            logger.info(msg)

    def _route_node(self, state: WarpSenseState) -> dict:
        features = state["features"]
        violations = compute_violations(features)
        t_trig = thermal_triggered(features)
        g_trig = geometry_triggered(features)
        p_trig = process_triggered(features)
        self._log(
            f"[Graph] Route: thermal={t_trig}, geometry={g_trig}, process={p_trig}, violations={len(violations)}"
        )
        return {
            "violations": violations,
            "routing_decision": {
                "thermal_triggered": t_trig,
                "geometry_triggered": g_trig,
                "process_triggered": p_trig,
            },
        }

    def _thermal_node(self, state: WarpSenseState) -> dict:
        result = self._thermal.run(
            state["prediction"], state["features"], state["violations"]
        )
        self._log(
            f"[Graph] ThermalAgent: {result.disposition} (triggered={result.triggered})"
        )
        return {"thermal_result": result}

    def _geometry_node(self, state: WarpSenseState) -> dict:
        result = self._geometry.run(
            state["prediction"], state["features"], state["violations"]
        )
        self._log(
            f"[Graph] GeometryAgent: {result.disposition} (triggered={result.triggered})"
        )
        return {"geometry_result": result}

    def _process_node(self, state: WarpSenseState) -> dict:
        result = self._process.run(
            state["prediction"], state["features"], state["violations"]
        )
        self._log(
            f"[Graph] ProcessStabilityAgent: {result.disposition} (triggered={result.triggered})"
        )
        return {"process_result": result}

    def _summary_node(self, state: WarpSenseState) -> dict:
        results = [
            r
            for r in [
                state["thermal_result"],
                state["geometry_result"],
                state["process_result"],
            ]
            if r is not None
        ]
        report = self._summary.synthesise(
            results, state["prediction"], state["features"], state["violations"]
        )
        self._log(f"[Graph] SummaryAgent: {report.disposition}")
        return {"final_report": report}

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

    def assess(
        self, prediction: WeldPrediction, features: SessionFeatures
    ) -> WeldQualityReport:
        session_id = getattr(prediction, "session_id", "unknown")
        initial_state: WarpSenseState = {
            "session_id": session_id,
            "features": features,
            "prediction": prediction,
            "violations": [],
            "routing_decision": {},
            "thermal_result": None,
            "geometry_result": None,
            "process_result": None,
            "final_report": None,
        }
        final_state = self._graph.invoke(initial_state)
        report = final_state.get("final_report")
        if report is None:
            raise RuntimeError(
                f"[WarpSenseGraph] final_report is None for session {session_id}"
            )
        return report

    def assess_with_progress(
        self,
        prediction: WeldPrediction,
        features: SessionFeatures,
        progress_cb=None,
    ) -> WeldQualityReport:
        """
        Run the WarpSense pipeline with per-stage progress callbacks.

        Calls internal node methods in the same order as assess() but fires
        progress_cb(event_dict) between each agent stage. Used by the SSE route
        to emit live progress events to the frontend.

        progress_cb is called from whatever thread this method runs in.
        When called via run_in_executor, the caller must use
        loop.call_soon_threadsafe to forward events to the event loop.

        assess() is unchanged and remains the primary method for non-SSE callers.
        """

        def _emit(event: dict) -> None:
            if progress_cb is not None:
                progress_cb(event)

        session_id = getattr(prediction, "session_id", "unknown")

        state: WarpSenseState = {
            "session_id": session_id,
            "features": features,
            "prediction": prediction,
            "violations": [],
            "routing_decision": {},
            "thermal_result": None,
            "geometry_result": None,
            "process_result": None,
            "final_report": None,
        }

        # Route node — computes violations and routing_decision (fast, no progress event)
        state.update(self._route_node(state))

        # Thermal agent
        _emit(
            {
                "stage": "thermal_agent",
                "status": "running",
                "message": "Analysing heat profile",
            }
        )
        try:
            state.update(self._thermal_node(state))
        except Exception:
            _emit({"stage": "thermal_agent", "status": "done", "disposition": None})
            raise
        _emit(
            {
                "stage": "thermal_agent",
                "status": "done",
                "disposition": state["thermal_result"].disposition,
            }
        )

        # Geometry agent
        _emit(
            {
                "stage": "geometry_agent",
                "status": "running",
                "message": "Checking torch angle",
            }
        )
        try:
            state.update(self._geometry_node(state))
        except Exception:
            _emit({"stage": "geometry_agent", "status": "done", "disposition": None})
            raise
        _emit(
            {
                "stage": "geometry_agent",
                "status": "done",
                "disposition": state["geometry_result"].disposition,
            }
        )

        # Process stability agent
        _emit(
            {
                "stage": "process_agent",
                "status": "running",
                "message": "Evaluating arc stability",
            }
        )
        try:
            state.update(self._process_node(state))
        except Exception:
            _emit({"stage": "process_agent", "status": "done", "disposition": None})
            raise
        _emit(
            {
                "stage": "process_agent",
                "status": "done",
                "disposition": state["process_result"].disposition,
            }
        )

        # Summary agent (LLM synthesis — slow step)
        _emit(
            {"stage": "summary", "status": "running", "message": "Synthesising report"}
        )
        state.update(self._summary_node(state))

        report = state.get("final_report")
        if report is None:
            raise RuntimeError(
                f"[WarpSenseGraph] assess_with_progress: final_report is None for session {session_id}"
            )
        return report
