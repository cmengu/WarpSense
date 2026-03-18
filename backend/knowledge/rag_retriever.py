"""
RAGRetriever — Hybrid dense + sparse retrieval with RRF merge.

Extracts retrieval logic from BaseSpecialistAgent into a standalone facade.
BM25 index built once at construction; specialists call retrieve(queries)
and receive list[StandardsChunk]. Used by WarpSenseGraph-instantiated specialists.
"""

from pathlib import Path
from typing import Literal, Optional
import sys

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from backend.agent.warpsense_agent import StandardsChunk, ThresholdViolation

_KB_PATH = Path(__file__).resolve().parent / "chroma_db"
_COLLECTION_NAME = "welding_standards"


def decompose_queries(
    base_queries: list[str],
    violations: list["ThresholdViolation"],
    domain: Literal["thermal", "geometry", "process"],
) -> list[str]:
    """
    Expand specialist query strings with violation-specific numeric terms.
    Module-level function — testable without instantiating RAGRetriever.

    base_queries: specialist-generated query strings (_get_queries() output)
    violations:   list[ThresholdViolation] — own_violations for this specialist
    domain:       specialist domain — adds a domain-level anchor query

    Returns deduplicated list, max 5 queries.
    """
    expanded = list(base_queries)

    for v in violations[:2]:
        feature_slug = v.feature.replace("_", " ")
        unit_str = f" {v.unit}" if v.unit else ""
        expanded.append(
            f"{feature_slug} {v.value:.1f}{unit_str} corrective action threshold"
        )

    domain_anchors = {
        "thermal":  "heat input thermal instability LOF LOP corrective protocol",
        "geometry": "torch angle deviation fusion boundary corrective work angle",
        "process":  "arc stability process parameter WPS bounds corrective action",
    }
    expanded.append(domain_anchors[domain])

    seen: set[str] = set()
    unique: list[str] = []
    for q in expanded:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique[:5]


class RAGRetriever:
    """
    Hybrid dense + sparse retriever with RRF merge.

    BM25 index is built ONCE at construction from the full ChromaDB corpus.
    Subsequent retrieve() calls reuse self._bm25 — no rebuild per query.

    Three fields are declared at object level and populated by _build_bm25_index():
      self._bm25         — BM25Okapi instance
      self._chunk_ids    — parallel list of chunk IDs matching BM25 corpus order
      self._chunk_texts  — parallel list of chunk texts
      self._chunk_metas  — parallel list of chunk metadata dicts

    mode="hybrid"  RRF merge of ChromaDB cosine + BM25 (default, production)
    mode="dense"   ChromaDB cosine only (eval baseline)
    mode="sparse"  BM25 only (eval ablation)
    """

    def __init__(
        self,
        chroma_client: Optional[chromadb.PersistentClient] = None,
        chroma_path: Optional[str] = None,
        collection_name: str = _COLLECTION_NAME,
        n_results: int = 4,
        rrf_k: int = 60,
        verbose: bool = True,
    ):
        self.n_results = n_results
        self.rrf_k = rrf_k
        self.verbose = verbose

        # ── Dense (ChromaDB) ──────────────────────────────────────────
        if chroma_client is not None:
            client = chroma_client
        else:
            client = chromadb.PersistentClient(
                path=chroma_path or str(_KB_PATH)
            )
        ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = client.get_collection(
            name=collection_name, embedding_function=ef
        )

        # _dense_retrieve converts ChromaDB distances to scores via (1 - dist),
        # which is only valid under cosine distance.  Fail loudly if the
        # collection was created with a different space.
        space = (self._collection.metadata or {}).get("hnsw:space", "cosine")
        if space != "cosine":
            raise ValueError(
                f"[RAGRetriever] Expected hnsw:space='cosine' but got '{space}'. "
                "Dense score formula (1 - dist) is only valid for cosine distance."
            )

        # ── Sparse (BM25) — fields declared here, populated below ─────
        # Declared at object level so every method can safely read them
        # without checking for attribute existence.
        self._bm25: Optional[BM25Okapi] = None
        self._chunk_ids: list[str] = []
        self._chunk_texts: list[str] = []
        self._chunk_metas: list[dict] = []

        self._build_bm25_index()

        if self.verbose:
            print(
                f"[RAGRetriever] {len(self._chunk_ids)} chunks loaded. "
                f"BM25 ready."
            )

    def _build_bm25_index(self) -> None:
        """
        Fetch full corpus from ChromaDB and build BM25 index.
        Called once from __init__. Fails loudly if corpus is empty — correct.
        """
        all_docs = self._collection.get(include=["documents", "metadatas"])
        self._chunk_ids = all_docs["ids"]
        self._chunk_texts = all_docs["documents"]
        self._chunk_metas = all_docs["metadatas"]

        if not self._chunk_ids:
            raise RuntimeError(
                "[RAGRetriever] ChromaDB collection is empty. "
                "Run build_welding_kb.py before initialising RAGRetriever."
            )

        tokenized = [doc.lower().split() for doc in self._chunk_texts]
        self._bm25 = BM25Okapi(tokenized)

    # ── Dense ──────────────────────────────────────────────────────────

    def _dense_retrieve(self, query: str, n: int) -> list[tuple[str, float]]:
        """Returns [(chunk_id, cosine_score), ...] sorted descending."""
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n, len(self._chunk_ids)),
            include=["distances"],
        )
        return [
            (chunk_id, round(1 - dist, 4))
            for chunk_id, dist in zip(
                results["ids"][0], results["distances"][0]
            )
        ]

    # ── Sparse ─────────────────────────────────────────────────────────

    def _sparse_retrieve(self, query: str, n: int) -> list[tuple[str, float]]:
        """Returns [(chunk_id, bm25_score), ...] sorted descending."""
        assert self._bm25 is not None, (
            "_sparse_retrieve called before BM25 index was built"
        )
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self._chunk_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(cid, float(s)) for cid, s in ranked[:n]]

    # ── RRF merge ──────────────────────────────────────────────────────

    def _rrf_merge(
        self,
        dense_ranked: list[tuple[str, float]],
        sparse_ranked: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        """
        Reciprocal Rank Fusion — uses rank position only, not raw scores.
        Safe to merge cosine similarity (0–1) and BM25 scores (unbounded).
        rrf_score = 1/(k + rank_dense) + 1/(k + rank_sparse)
        Chunks appearing in only one list get rank = len(list) + 1 (penalty).
        """
        k = self.rrf_k
        dense_ids = [cid for cid, _ in dense_ranked]
        sparse_ids = [cid for cid, _ in sparse_ranked]
        all_ids = set(dense_ids) | set(sparse_ids)

        rrf: dict[str, float] = {}
        for cid in all_ids:
            rd = (
                dense_ids.index(cid) + 1
                if cid in dense_ids
                else len(dense_ids) + 1
            )
            rs = (
                sparse_ids.index(cid) + 1
                if cid in sparse_ids
                else len(sparse_ids) + 1
            )
            rrf[cid] = 1 / (k + rd) + 1 / (k + rs)

        return sorted(rrf.items(), key=lambda x: x[1], reverse=True)

    # ── Hydrate ────────────────────────────────────────────────────────

    def _hydrate(self, chunk_ids: list[str]) -> list[StandardsChunk]:
        """Convert chunk_ids → list[StandardsChunk] using in-memory corpus."""
        id_to_idx = {cid: i for i, cid in enumerate(self._chunk_ids)}
        result = []
        for cid in chunk_ids:
            idx = id_to_idx.get(cid)
            if idx is None:
                continue
            meta = self._chunk_metas[idx]
            result.append(StandardsChunk(
                chunk_id=cid,
                text=self._chunk_texts[idx],
                source=meta.get("source", "unknown"),
                section=meta.get("section", ""),
                score=0.0,
            ))
        return result

    # ── Public interface ───────────────────────────────────────────────

    def retrieve(
        self,
        queries: list[str],
        mode: Literal["hybrid", "dense", "sparse"] = "hybrid",
    ) -> list[StandardsChunk]:
        """
        Called by specialists. Returns list[StandardsChunk].

        mode default "hybrid" — call sites never need to pass mode.
        mode="dense"/"sparse" used only in eval ablation.

        Deduplicates across multiple queries by keeping best score per chunk.
        Per-query fault tolerance: failed queries are logged and skipped.
        """
        n_per_query = max(self.n_results * 2, 10)
        candidate_pool: dict[str, float] = {}

        for query in queries[:5]:
            try:
                if mode == "dense":
                    for cid, score in self._dense_retrieve(query, n_per_query):
                        candidate_pool[cid] = max(candidate_pool.get(cid, 0.0), score)

                elif mode == "sparse":
                    for cid, score in self._sparse_retrieve(query, n_per_query):
                        candidate_pool[cid] = max(candidate_pool.get(cid, 0.0), score)

                else:  # hybrid
                    dense = self._dense_retrieve(query, n_per_query)
                    sparse = self._sparse_retrieve(query, n_per_query)
                    for cid, score in self._rrf_merge(dense, sparse):
                        candidate_pool[cid] = max(candidate_pool.get(cid, 0.0), score)
            except Exception as e:
                if self.verbose:
                    print(f"[RAGRetriever] query failed (skipping): {e}")

        top_ids = [
            cid for cid, _ in sorted(
                candidate_pool.items(), key=lambda x: x[1], reverse=True
            )
        ][: self.n_results]

        return self._hydrate(top_ids)
