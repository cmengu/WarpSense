# Integrate On-Device AI Function Calling via FunctionGemma

**Type:** Feature | **Priority:** High | **Effort:** Medium

---

## TL;DR

Add a welding-specific AI function-calling engine to WarpSense backend that routes simple queries on-device (FunctionGemma 270M via Cactus) and complex/open-ended queries to cloud (Gemini), exposing it via a FastAPI route and terminal demo for judges.

---

## Current State

- No AI function-calling layer exists in WarpSense
- FunctionGemma code exists in a separate repo, tuned for phone assistant tasks (alarms, music, reminders) — not welding

---

## Expected Outcome

- `POST /api/ai/analyze` accepts a natural language query about weld data
- Simple threshold/score queries resolve on-device in <500ms (`source: on-device`)
- Complex open-ended queries fall back to Gemini (`source: cloud`)
- `python backend/weld_demo.py` runs 3 scenarios showing both paths in terminal

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/cactus/` | Copied from FunctionGemma repo — relative paths, self-contained |
| `backend/function_gemma.py` | Adapted engine (welding prompt, numeric recovery, cloud re-enabled) |
| `backend/warp_tools.py` | 3 tool definitions: `check_parameter_threshold`, `evaluate_session_score`, `flag_anomaly` |
| `backend/weld_demo.py` | 3 judge-facing terminal scenarios |
| `backend/routes/ai.py` | Thin FastAPI wrapper |

---

## Files to Touch

| File | Change |
|------|--------|
| `backend/main.py` | 2 lines only: import + `include_router` |

---

## Key Changes vs Source FunctionGemma

- **Replace `_BASE_SYSTEM_PROMPT`** — swap phone examples for welding examples
- **Replace `_TOOL_ACTION_VERBS`** — welding verbs (check, flag, evaluate)
- **Replace `_recover_arguments`** — recover numeric sensor values + session IDs instead of times/contacts
- **Simplify `_validate_tool_call`** — remove hour/minute range guards (breaks on voltages like 28V)
- **Re-enable cloud fallback** in `generate_hybrid` — disabled in source for hackathon scoring reasons

---

## Demo Scenarios

1. **Angle too high** → on-device
2. **Voltage out of range** → on-device
3. **Low session score + "why?"** → cloud

---

## Implementation Notes

- **Cactus path:** Copy entire `cactus/` folder from FunctionGemma repo into `backend/`. Use relative paths: `sys.path.insert(0, "backend/cactus/python/src")`, `functiongemma_path = "backend/cactus/weights/functiongemma-270m-it"`. No hardcoded `/Users/...` — repo is self-contained.
- **Session ID:** Recovery targets `WS-\d+` format only (matches mock data). Skip `sess_*` for demo; post-hackathon concern if real DB differs.
- **Cloud fallback errors:** Return 200 with `{ "source": "cloud_error", "error": "GEMINI_API_KEY not set", "function_calls": [] }` — not 503. Wrap `generate_cloud` in try/except for missing key and API errors.
- **Tool execution:** Return parsed `function_calls` JSON only — no DB lookups. Judges see AI deciding what to call. Demo script can pretty-print interpretation client-side.

---

## Risks & Notes

- **`GEMINI_API_KEY`** must be exported for cloud fallback; if unset, response includes `source: "cloud_error"` and error message
- **FunctionGemma 270M** may hallucinate tool args on ambiguous queries — recovery heuristics are regex-based and fragile outside the 3 demo scenarios

---

## Vision

Shows judges WarpSense has a real-time, privacy-preserving AI layer — simple quality checks never leave the device, complex coaching queries escalate to cloud. Differentiates from dashboards that just display data.
