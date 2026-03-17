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
    from backend.agent.warpsense_graph import WarpSenseGraph
    graph = WarpSenseGraph()
    report = graph.assess(prediction, features)  # → WeldQualityReport
"""

import sys
from pathlib import Path
from typing import Dict, Optional, TypedDict

_ROOT = Path(__file__).resolve().parent.parent.parent
_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "chroma_db"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chromadb
from chromadb.utils import embedding_functions
from groq import Groq

from backend.agent.warpsense_agent import LLM_MODEL, WeldQualityReport
from backend.agent.specialists import (
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
from backend.features.session_feature_extractor import SessionFeatures
from backend.features.weld_classifier import WeldPrediction


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
        ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = client.get_collection(name=collection_name, embedding_function=ef)

        import os
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        self._thermal  = ThermalAgent(groq_client, self._collection, llm_model, n_chunks_per_specialist, verbose)
        self._geometry = GeometryAgent(groq_client, self._collection, llm_model, n_chunks_per_specialist, verbose)
        self._process  = ProcessStabilityAgent(groq_client, self._collection, llm_model, n_chunks_per_specialist, verbose)
        self._summary  = SummaryAgent()

        self._graph = self._build_graph()

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

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

    def assess(self, prediction: WeldPrediction, features: SessionFeatures) -> WeldQualityReport:
        session_id = getattr(prediction, "session_id", "unknown")
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
        final_state = self._graph.invoke(initial_state)
        report = final_state.get("final_report")
        if report is None:
            raise RuntimeError(f"[WarpSenseGraph] final_report is None for session {session_id}")
        return report
