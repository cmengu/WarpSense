# FunctionGemma On-Device AI — Exploration

> **Purpose:** Pre-implementation exploration. No code changes yet.  
> **Source:** `.cursor/issues/function-gemma-on-device-ai.md` + user plan (v2 FunctionGemma)  
> **Date:** 2026-02-21

---

## 1. Current Codebase Snapshot

### Backend Structure

```
backend/
├── main.py              # FastAPI app, CORS, lifespan, route registration
├── database/            # Connection, models (SessionModel, FrameModel, etc.)
├── models/              # Pydantic (Session, Frame, SessionScore, etc.)
├── routes/              # 11 route modules (sessions, narratives, predictions, etc.)
├── services/            # narrative_service, scoring_service, threshold_service, etc.
├── scoring/             # rule_based.py (5 rules)
├── features/            # extractor.py (5 features from frames)
└── data/                # mock_sessions, mock_welders
```

### Existing AI Integration

| Component | Provider | Purpose |
|-----------|----------|---------|
| `narrative_service.py` | **Anthropic (Claude)** | Session narrative generation, cached in `session_narratives` |
| `prediction_service.py` | ONNX (local) | Warp risk prediction from frame window |

**No Gemini in WarpSense today.** Plan introduces Gemini as new cloud fallback for AI analyze.

### Session & Frame Schema

| Entity | Key Fields |
|--------|------------|
| **Session** | `session_id` (e.g. `sess_expert_001`, `sess_novice_001`, `sess_{welder_id}_{i:03d}`), `operator_id`, `weld_type`, `score_total`, `process_type` |
| **Frame** | `timestamp_ms`, `volts`, `amps`, `angle_degrees`, `thermal_snapshots`, `heat_dissipation_rate_celsius_per_sec` |
| **Score** | `total` (0–100), `rules` (rule_id, threshold, passed, actual_value) |

**Parameter alignment:** WarpSense frames have `volts`, `amps`, `angle_degrees`. Plan tools use `voltage`, `current`, `angle`, `wire_feed_speed`, `travel_speed`. WarpSense does **not** have `wire_feed_speed` or `travel_speed` in frames — only in thresholds/features indirectly.

### Route Registration Pattern

```python
# main.py
app.include_router(aggregate_router, prefix="/api")   # → /api/sessions/aggregate
app.include_router(predictions_router)               # router has prefix="/api/sessions" → /api/sessions/{id}/warp-risk
app.include_router(narratives.router)                # prefix="/api/sessions" → /api/sessions/{id}/narrative
```

For `POST /api/ai/analyze`:
- `router = APIRouter(prefix="/ai", tags=["ai"])`
- `@router.post("/analyze")`
- `app.include_router(ai_router, prefix="/api")` → `/api/ai/analyze`

---

## 2. Data Flow (How It Would Work)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  User / Judge                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         │  "voltage is 28V but acceptable range is 18 to 24 volts"
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  POST /api/ai/analyze  { "query": "..." }                                        │
│  backend/routes/ai.py                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         │  messages = [{"role": "user", "content": query}]
         │  tools = WARP_TOOLS
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  generate_hybrid(messages, tools)                                                │
│  backend/function_gemma.py                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ├──► Try on-device (FunctionGemma 270M via Cactus)
         │    - Parse query → tool call JSON
         │    - _recover_arguments (numeric, session_id)
         │    - _validate_tool_call
         │    - If valid: return { source: "on-device", function_calls, total_time_ms }
         │
         └──► If invalid / complex / open-ended:
              - generate_cloud(messages, tools)  ← Gemini API
              - return { source: "cloud", ... }
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Response: { source, function_calls?, total_time_ms, ... }                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Demo path:** `python backend/weld_demo.py` (run from project root) → same `generate_hybrid` call, prints to terminal.

---

## 3. Component Structure (High-Level Mock)

### New Files

| File | Responsibility |
|------|----------------|
| `backend/function_gemma.py` | Engine: Cactus sys.path, prompt, tool parsing, recovery, validation, cloud fallback |
| `backend/warp_tools.py` | `WARP_TOOLS` list (3–5 tool defs in OpenAI function-calling schema) |
| `backend/weld_demo.py` | 3 scenarios, calls `generate_hybrid`, prints SOURCE/TIME/TOOL/ARGS |
| `backend/routes/ai.py` | `POST /analyze` → parse body → `generate_hybrid` → return JSON |

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | `from routes.ai import router as ai_router` + `app.include_router(ai_router, prefix="/api")` |

### Pseudocode: ai.py Route

```
POST /api/ai/analyze
  Request: { query: string }
  Response: { source: "on-device"|"cloud", function_calls?: [...], total_time_ms: number, ... }

  - Validate query non-empty
  - result = generate_hybrid([{role: "user", content: query}], WARP_TOOLS)
  - return result
```

### Pseudocode: generate_hybrid (conceptual)

```
generate_hybrid(messages, tools):
  t0 = now()
  # 1. Try on-device
  system_prompt = _BASE_SYSTEM_PROMPT  # welding examples
  on_device = run_cactus(messages, tools, system_prompt)
  parsed = parse_tool_calls(on_device)
  parsed = _recover_arguments(parsed, tools, last_user_message)
  if _validate_tool_call(parsed, tools):
    return { source: "on-device", function_calls: parsed, total_time_ms: now()-t0 }
  # 2. Cloud fallback
  cloud = generate_cloud(messages, tools)  # Gemini
  cloud["source"] = "cloud"
  cloud["total_time_ms"] = now() - t0
  return cloud
```

---

## 4. State Management & Side Effects

| Layer | State | Side Effects |
|-------|-------|--------------|
| **Route** | Stateless | Reads `query` from body, returns JSON |
| **function_gemma** | Module-level Cactus path, model load | One-time Cactus init; Gemini HTTP call on fallback |
| **weld_demo** | None | Pure script: run scenarios, print |

**No DB writes.** AI analyze is stateless. No caching (unlike narratives).

---

## 5. Edge Cases

| Case | Handling |
|------|----------|
| **Empty query** | 400 Bad Request |
| **Cactus path missing** | Cactus copied into `backend/` — relative path; fails only if copy incomplete |
| **GEMINI_API_KEY unset** (cloud fallback) | Return `{ source: "cloud_error", error: "...", function_calls: [] }` — 200, not 503 |
| **Ambiguous query** | 270M may hallucinate args; recovery heuristics may fail → falls through to cloud |
| **Multi-tool query** ("check voltage and flag session") | Plan mentions `_split_into_actions` — verify v2 supports |
| **Session ID format** | `WS-\d+` only; matches mock data |

---

## 6. Parameter & Tool Alignment

**Plan tools:** `check_parameter_threshold(parameter, value, min_threshold, max_threshold)` with params: `voltage`, `current`, `angle`, `wire_feed_speed`, `travel_speed`.

**WarpSense reality:**
- Frame: `volts`, `amps`, `angle_degrees` ✓
- No `wire_feed_speed`, `travel_speed` in frame schema
- Features: `amps_stddev`, `angle_max_deviation`, `volts_range`, etc. (aggregates, not per-frame)

**Recommendation:** Limit `check_parameter_threshold` to `voltage`, `current`, `angle` for MVP. Add `wire_feed_speed`/`travel_speed` only if schema extended.

---

## 7. Implementation Approach

### File Tree

```
backend/
  function_gemma.py   (NEW) — Full engine from v2, adapted per plan Steps 1–6
  warp_tools.py       (NEW) — WARP_TOOLS, 3 tools (or 5 if get_session_summary, compare_welder added)
  weld_demo.py        (NEW) — 3 scenarios, run from project root
  routes/
    ai.py             (NEW) — POST /analyze, thin wrapper
  main.py             (MODIFY) — 2 lines: import + include_router
```

### Why This Structure

- **function_gemma.py** — Isolated; no FastAPI deps. Can be tested/demo'd without server.
- **warp_tools.py** — Single source of truth for tool defs; route and demo both import.
- **weld_demo.py** — Standalone script for judges; no server required.
- **routes/ai.py** — Thin; all logic in function_gemma.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Put engine in `services/ai_analyze_service.py` | Plan explicitly puts everything in `function_gemma.py`; keeps Cactus coupling local |
| Use Claude for cloud fallback (match narratives) | Plan specifies Gemini; adds new provider for this feature |
| Add tool execution (actually call DB) | Plan describes tool *parsing* only; execution is out of scope for demo |

---

## 8. Resolved Decisions

1. **Cactus path:** Copy entire `cactus/` folder from FunctionGemma repo into `backend/`. Relative paths: `sys.path.insert(0, "backend/cactus/python/src")`, `functiongemma_path = "backend/cactus/weights/functiongemma-270m-it"`. Self-contained, no hardcoded `/Users/...`.

2. **Session ID:** Use `WS-\d+` only. Mock data generates this format. Skip `sess_*` recovery for demo.

3. **Cloud fallback failure:** Return 200 with `{ "source": "cloud_error", "error": "GEMINI_API_KEY not set", "function_calls": [] }`. Wrap `generate_cloud` in try/except for missing key and API errors. No 503.

4. **Tool execution:** Return parsed `function_calls` JSON only — no DB lookups. Demo script can pretty-print client-side.

---

## 9. Summary

| Aspect | Status |
|--------|--------|
| **Integration points** | Clear: new route, new engine, no changes to existing AI (narratives) |
| **Data flow** | Query → generate_hybrid → on-device or cloud (or cloud_error) → JSON response |
| **Dependencies** | Cactus (copied into backend/), Gemini API (new), no new DB tables |
| **Risks** | Silent cloud failure → now returns cloud_error; regex fragility remains |
| **Schema alignment** | Session ID: WS-\d+ only |

**Ready for implementation.**
