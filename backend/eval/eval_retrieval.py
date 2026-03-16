"""
eval_retrieval.py
-----------------
Evaluates ChromaDB retrieval quality against 25 ground-truth query→chunk_id pairs.

Metrics:
  Precision@k = |retrieved ∩ relevant| / k
  Recall@k    = |retrieved ∩ relevant| / |relevant|
  MRR         = mean(1 / rank_of_first_relevant_doc)

Varies k = 1, 2, 3, 5, 6 (6 = actual agent operating point).
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = _ROOT / "backend" / "knowledge" / "chroma_db"
COLLECTION_NAME = "welding_standards"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

K_VALUES = [1, 2, 3, 5, 6]


@dataclass
class RetrievalQuery:
    query_id: str
    query: str
    relevant_ids: list[str]
    category: str


GROUND_TRUTH: list[RetrievalQuery] = [
    RetrievalQuery("RQ_001", "lack of fusion acceptance criteria ISO 5817 all quality levels", ["iso5817_lof_all_levels", "aws_d11_lof_zero_tolerance", "iso5817_lof_fillet_welds"], "lof"),
    RetrievalQuery("RQ_002", "torch angle deviation 45 degrees lack of fusion root cause", ["torch_angle_work_angle", "torch_angle_variability_consequence", "corrective_lof_angle_drift"], "lof"),
    RetrievalQuery("RQ_003", "corrective action for angle deviation mean exceeding 15 degrees", ["corrective_lof_angle_drift", "torch_angle_work_angle", "warpsense_feature_thresholds"], "lof"),
    RetrievalQuery("RQ_004", "stitch welding restart cold interface lack of fusion risk", ["stitch_welding_risk", "corrective_lof_cold_window", "warpsense_arc_on_ratio"], "lof"),
    RetrievalQuery("RQ_005", "incomplete fusion AWS D1.1 rejection criterion repair", ["aws_d11_lof_zero_tolerance", "aws_d11_table81_fusion", "aws_d11_disposition_rework"], "lof"),
    RetrievalQuery("RQ_006", "LOF LOP invisible to X-ray visual inspection shipyard NDT", ["warpsense_lof_lop_invisible_inspection", "iacs47_weld_ndt_coverage", "ndt_method_selection"], "lof"),
    RetrievalQuery("RQ_007", "incomplete root penetration ISO 5817 quality level D acceptance", ["iso5817_incomplete_root_penetration", "root_cause_lop_primary"], "lop"),
    RetrievalQuery("RQ_008", "cold arc window low heat input minimum rolling incomplete penetration", ["corrective_lof_cold_window", "root_cause_lop_primary", "iacs47_high_heat_input_threshold"], "lop"),
    RetrievalQuery("RQ_009", "heat input too low amperage insufficient LOF LOP causes", ["heat_input_amperage_effect", "root_cause_lof_primary", "root_cause_lop_primary"], "lop"),
    RetrievalQuery("RQ_010", "heat dissipation spike 65 degrees per second corrective action", ["corrective_lof_thermal_instability", "heat_dissipation_significance"], "thermal"),
    RetrievalQuery("RQ_011", "heat_diss_max_spike threshold expert novice benchmark", ["heat_dissipation_significance", "warpsense_heat_input_expert_novice", "warpsense_feature_thresholds"], "thermal"),
    RetrievalQuery("RQ_012", "rapid cooling rate preheat hydrogen cracking risk", ["iacs47_preheat", "root_cause_cracking", "heat_dissipation_significance"], "thermal"),
    RetrievalQuery("RQ_013", "heat input drop severity stitch transition corrective reduce variance", ["corrective_lof_thermal_instability", "stitch_welding_risk", "heat_input_travel_speed_effect"], "thermal"),
    RetrievalQuery("RQ_014", "porosity root cause moisture shielding gas humidity", ["root_cause_porosity", "humidity_tropical_context", "corrective_porosity_heat_diss"], "porosity"),
    RetrievalQuery("RQ_015", "voltage CV instability porosity arc length corrective", ["heat_input_voltage_effect", "corrective_porosity_heat_diss", "root_cause_porosity"], "porosity"),
    RetrievalQuery("RQ_016", "ISO 5817 porosity surface pore quality level acceptance", ["iso5817_porosity_surface", "aws_d11_table81_porosity_static"], "porosity"),
    RetrievalQuery("RQ_017", "undercut acceptance criteria ISO 5817 level C maximum depth", ["iso5817_undercut", "aws_d11_table81_undercut_static", "aws_d11_table81_undercut_cyclic"], "undercut"),
    RetrievalQuery("RQ_018", "undercut corrective reduce amperage torch angle 45 degrees", ["corrective_undercut_high_heat", "root_cause_undercut", "torch_angle_work_angle"], "undercut"),
    RetrievalQuery("RQ_019", "WarpSense feature thresholds GOOD MARGINAL RISK bands", ["warpsense_feature_thresholds", "warpsense_defect_feature_map"], "threshold"),
    RetrievalQuery("RQ_020", "WarpSense quality class GOOD MARGINAL DEFECTIVE ISO 5817 mapping", ["warpsense_quality_class_mapping", "iso5817_overview", "iso5817_level_selection"], "threshold"),
    RetrievalQuery("RQ_021", "corrective parameter bounds WPS amperage voltage travel speed limits", ["corrective_parameter_bounds", "aws_d11_wps_essential_variables"], "threshold"),
    RetrievalQuery("RQ_022", "disposition framework REWORK REQUIRED CONDITIONAL PASS criteria", ["disposition_framework", "warpsense_quality_class_mapping", "aws_d11_disposition_rework"], "threshold"),
    RetrievalQuery("RQ_023", "IACS recommendation 47 shipyard weld quality inspection coverage", ["iacs47_weld_ndt_coverage", "iacs47_scope", "research_amirafshari_2022"], "system"),
    RetrievalQuery("RQ_024", "marine welding tropical humidity Singapore moisture porosity", ["humidity_tropical_context", "iacs47_marine_environment_context", "iacs47_preheat"], "system"),
    RetrievalQuery("RQ_025", "heat input formula kJ/mm voltage amperage travel speed calculation", ["aws_d11_heat_input_formula", "heat_input_formula_physics"], "system"),
]


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant) if relevant else 0.0


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


@dataclass
class QueryResult:
    query_id: str
    query: str
    category: str
    retrieved_ids: list[str]
    relevant_ids: list[str]
    rr: float
    p_at_k: dict
    r_at_k: dict


@dataclass
class RetrievalEvalReport:
    timestamp: str
    n_queries: int
    k_values: list[int]
    mrr: float
    mean_p_at_k: dict
    mean_r_at_k: dict
    by_category: dict
    query_results: list


class RetrievalEvaluator:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._log(f"[RAGEval] Loading ChromaDB from {CHROMA_PATH}")
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
        self._log(f"[RAGEval] Collection loaded: {self.collection.count()} chunks")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _retrieve(self, query: str, k: int) -> list[str]:
        # Chroma returns ids by default; include must not contain "ids" on newer versions.
        results = self.collection.query(query_texts=[query], n_results=k, include=["documents"])
        return results["ids"][0]

    def _eval_query(self, q: RetrievalQuery, max_k: int) -> QueryResult:
        retrieved = self._retrieve(q.query, max_k)
        rr = reciprocal_rank(retrieved, q.relevant_ids)
        p_at_k = {k: precision_at_k(retrieved, q.relevant_ids, k) for k in K_VALUES if k <= max_k}
        r_at_k = {k: recall_at_k(retrieved, q.relevant_ids, k) for k in K_VALUES if k <= max_k}
        return QueryResult(q.query_id, q.query, q.category, retrieved, q.relevant_ids, rr, p_at_k, r_at_k)

    def evaluate(self, queries: Optional[list[RetrievalQuery]] = None, k_values: list[int] = K_VALUES) -> RetrievalEvalReport:
        queries = queries or GROUND_TRUTH
        max_k = max(k_values)

        self._log(f"\n{'=' * 60}")
        self._log(f"RAG RETRIEVAL EVAL — {len(queries)} queries, k={k_values}")
        self._log(f"{'=' * 60}\n")

        qr_list = []
        for q in queries:
            qr = self._eval_query(q, max_k)
            qr_list.append(qr)
            hits = [cid for cid in qr.retrieved_ids[:3] if cid in q.relevant_ids]
            self._log(
                f"  {q.query_id}  RR={qr.rr:.2f}  P@3={qr.p_at_k.get(3,0):.2f}  "
                f"P@6={qr.p_at_k.get(6,0):.2f}  hits={hits}"
            )

        mrr = mean(qr.rr for qr in qr_list)
        mean_p = {k: mean(qr.p_at_k.get(k, 0) for qr in qr_list) for k in k_values}
        mean_r = {k: mean(qr.r_at_k.get(k, 0) for qr in qr_list) for k in k_values}

        categories = sorted(set(q.category for q in queries))
        by_cat = {}
        for cat in categories:
            cat_qrs = [qr for qr in qr_list if qr.category == cat]
            by_cat[cat] = {
                "n": len(cat_qrs),
                "mrr": mean(qr.rr for qr in cat_qrs),
                "p_at_3": mean(qr.p_at_k.get(3, 0) for qr in cat_qrs),
                "p_at_6": mean(qr.p_at_k.get(6, 0) for qr in cat_qrs),
                "r_at_6": mean(qr.r_at_k.get(6, 0) for qr in cat_qrs),
            }

        report = RetrievalEvalReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            n_queries=len(queries),
            k_values=k_values,
            mrr=mrr,
            mean_p_at_k={str(k): v for k, v in mean_p.items()},
            mean_r_at_k={str(k): v for k, v in mean_r.items()},
            by_category=by_cat,
            query_results=[asdict(qr) for qr in qr_list],
        )
        self._print_summary(report)
        return report

    def _print_summary(self, r: RetrievalEvalReport) -> None:
        w = 60
        print(f"\n{'=' * w}")
        print("RETRIEVAL EVAL SUMMARY")
        print(f"{'=' * w}")
        print(f"\nMRR:  {r.mrr:.3f}")
        print(f"\n{'k':<6} {'Precision@k':<18} {'Recall@k'}")
        print(f"{'-' * 40}")
        for k in r.k_values:
            pk = r.mean_p_at_k.get(str(k), 0)
            rk = r.mean_r_at_k.get(str(k), 0)
            marker = " ← current (n_standards_chunks=6)" if k == 6 else ""
            print(f"  {k:<4} {pk:<18.3f} {rk:.3f}{marker}")

        print("\nBy category:")
        print(f"  {'Category':<12} {'N':<5} {'MRR':<8} {'P@3':<8} {'P@6':<8} {'R@6'}")
        print(f"  {'-' * 50}")
        for cat, vals in sorted(r.by_category.items()):
            print(
                f"  {cat:<12} {vals['n']:<5} {vals['mrr']:<8.3f} "
                f"{vals.get('p_at_3', 0):<8.3f} {vals.get('p_at_6', 0):<8.3f} {vals.get('r_at_6', 0):.3f}"
            )

        print(f"\n{'=' * w}\n")
        print("Interpretation (based on P@6 — actual operating point):")
        p6 = r.mean_p_at_k.get("6", 0)
        if p6 >= 0.85:
            print(f"  P@6 = {p6:.2f} — retrieval strong. BM25 hybrid (Phase 5) likely not needed.")
        elif p6 >= 0.70:
            print(f"  P@6 = {p6:.2f} — retrieval adequate. BM25 hybrid worth building.")
        else:
            print(f"  P@6 = {p6:.2f} — retrieval weak. BM25 hybrid clearly justified.")

    def save(self, report: RetrievalEvalReport) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"retrieval_eval_{ts}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        print(f"[RAGEval] Results saved: {out}")
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description="WarpSense RAG retrieval evaluator")
    parser.add_argument("--k", type=int, nargs="+", default=K_VALUES)
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["lof", "lop", "thermal", "porosity", "undercut", "system", "threshold"],
    )
    parser.add_argument("--query", type=str, default=None)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    queries = GROUND_TRUTH
    if args.query:
        queries = [q for q in queries if q.query_id == args.query]
    elif args.category:
        queries = [q for q in queries if q.category == args.category]

    evaluator = RetrievalEvaluator(verbose=not args.quiet)
    report = evaluator.evaluate(queries=queries, k_values=args.k)
    if args.save:
        evaluator.save(report)


if __name__ == "__main__":
    main()
