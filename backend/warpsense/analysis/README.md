# analysis/ — the pure pipeline

**Role:** one function, `analyze(session_id, frames, *, classifier, graph,
progress_cb=None) -> AnalysisResult` — extract features, classify, assess.
Frames in, report out.

**Invariant — no I/O owned here.** Nothing in this package touches the DB,
FastAPI, or persistence, and nothing here is async. Frame loading lives in
`db/frames.py`; persistence lives in `services/warp_service.py`. `analyze()`
does block on network inside `graph.assess` (Groq LLM calls), so async
callers must run it in an executor.

**Imported by:** `services/` (warp_service, both the plain and SSE paths).
**Imports:** `features/`, `classifier/`, `agents/` — never `api/`,
`services/`, `db/`, or `realtime/`.

**Why the seam exists:** evaluating the pipeline against a corpus, swapping
the classifier, or replaying real sensor captures should not require a
database or a running server. Anything that can call `analyze()` with a
list of frame dicts gets the exact production pipeline.
