# FunctionGemma On-Device AI — Implementation Plan

**Overall Progress:** `~85%` (Step 1 deferred; Steps 4, 4b need Cactus)

---

## Implementation Status (Current)

### What We Built

| Step | Status | File(s) |
|------|--------|---------|
| Step 2 | ✅ Done | `backend/warp_tools.py` |
| Step 3 | ✅ Done | `backend/function_gemma.py` (stub when Cactus missing) |
| Step 6 | ✅ Done | `backend/weld_demo.py` |
| Step 5 | ✅ Done | `_generate_cloud` in function_gemma.py, `google-generativeai` in requirements.txt |
| Step 7 | ✅ Done | `backend/routes/ai.py` |
| Step 8 | ✅ Done | `main.py` — ai_router registered |
| Step 9 | ✅ Done | Unified routing in `generate_hybrid` |
| Step 10 | ✅ Done | `GET /api/ai/health` in routes/ai.py |
| Step 6b | ✅ Done | Privacy narrative, latency comparison, offline banner in weld_demo |
| Step 0 | ✅ Done | `backend/check_env.py` |
| Step 3b | ✅ Done | 2s timeout in `_generate_cloud` (ThreadPoolExecutor) |
| Step 1 | ⏸ Deferred | Copy Cactus when FunctionGemma repo ready |
| Step 4 | ⏸ Deferred | Welding prompt, recovery, validation — needs Cactus |
| Step 4b | ⏸ Deferred | Multi-turn chaining — needs spike + Cactus |

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WarpSense AI Layer                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   POST /api/ai/analyze          GET /api/ai/health      python weld_demo.py   │
│   (routes/ai.py)                (routes/ai.py)         (weld_demo.py)       │
│         │                              │                       │             │
│         └──────────────────────────────┼───────────────────────┘             │
│                                        ▼                                     │
│                         ┌──────────────────────────────┐                     │
│                         │   function_gemma.py           │                     │
│                         │   generate_hybrid(messages,  │                     │
│                         │   tools, offline)             │                     │
│                         └──────────────┬───────────────┘                     │
│                                        │                                     │
│                    ┌───────────────────┼───────────────────┐                 │
│                    ▼                   ▼                   ▼                 │
│         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐       │
│         │ Interrogative     │ │ On-Device        │ │ Validation       │       │
│         │ Gate             │ │ (Cactus or stub) │ │ + Escalation     │       │
│         │ why/explain +    │ │ _stub_on_device  │ │ _validate_tool   │       │
│         │ no measurement   │ │ when no Cactus   │ │ _call → cloud    │       │
│         └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘       │
│                  │                   │                   │                  │
│                  ▼                   │                   ▼                  │
│         ┌──────────────────┐         │          ┌──────────────────┐        │
│         │ Cloud (Gemini)   │         │          │ on-device→cloud  │        │
│         │ _generate_cloud  │         │          │ escalation       │        │
│         │ 2s timeout       │         │          └──────────────────┘        │
│         └──────────────────┘         │                                       │
│                  │                   │                                       │
│                  └───────────────────┴───────────────────┐                  │
│                                                          ▼                  │
│                                              {source, function_calls,       │
│                                               text, total_time_ms}          │
└─────────────────────────────────────────────────────────────────────────────┘

Data flow:
  warp_tools.py (WARP_TOOLS, ALLOWED_PARAMETERS)
       │
       ▼
  function_gemma.generate_hybrid
       │
       ├─► _is_interrogative + _has_measurement → route
       ├─► offline=True → OFFLINE_CANNED_RESPONSE for cloud-bound
       ├─► on-device: _stub_on_device_response (or Cactus when Step 1 done)
       ├─► _validate_tool_call (enum check) → escalate if invalid
       └─► _generate_cloud (Gemini) for interrogative queries
```

### File Map

| File | Purpose |
|------|---------|
| `backend/warp_tools.py` | WARP_TOOLS (3 tools), ALLOWED_PARAMETERS, enum constraint |
| `backend/function_gemma.py` | generate_hybrid, _generate_cloud, _stub_on_device_response, get_ai_health, routing |
| `backend/weld_demo.py` | 5 scenarios, --offline, privacy narrative, latency comparison |
| `backend/routes/ai.py` | POST /api/ai/analyze, GET /api/ai/health |
| `backend/check_env.py` | Pre-flight: Cactus/stub, weights, GEMINI_API_KEY, POST 200, concurrent, 5 scenarios |
| `backend/main.py` | app.include_router(ai_router) |

### Key Implementation Details

- **Stub mode:** When Cactus not imported, `_stub_on_device_response` returns plausible tool calls for demo queries. Demo and API work end-to-end.
- **Thread safety:** `_cactus_lock` around singleton init; `run_in_executor` in route prevents blocking.
- **Cloud timeout:** 2s via `ThreadPoolExecutor().submit(...).result(timeout=2)`.
- **Health honesty:** `gemini: "key_configured"` when key set — not `"ok"` (unverified).
- **Offline:** `{"source":"offline","text":"Cloud coaching unavailable offline..."}` for cloud-bound queries.

### Run Commands

```bash
# Demo (5 scenarios)
python backend/weld_demo.py
python backend/weld_demo.py --offline

# Pre-flight (run night before demo; server must be running)
python backend/check_env.py

# API (start server first: uvicorn main:app from backend/)
curl -X POST http://localhost:8000/api/ai/analyze -H "Content-Type: application/json" -d '{"query":"voltage 28V"}'
curl http://localhost:8000/api/ai/health
```

---

## Day-0 Blocker (Answer Before Proceeding)

**Has Cactus successfully imported on the exact machine we're demoing on?**

If the answer is **no**, the entire plan is blocked until it is. Step 1 has a 70% failure probability — a senior engineer should be alarmed. Everything after Step 1 is speculative architecture until Cactus runs on target hardware. Run the import test on the demo machine before writing any other code.

---

## TLDR

Add a welding-specific AI function-calling engine to WarpSense that routes simple queries on-device (FunctionGemma 270M via Cactus) and complex queries to cloud (Gemini). Expose via `POST /api/ai/analyze`, `GET /api/ai/health`, and `python backend/weld_demo.py`. **Multi-turn tool chaining** (evaluate → check → flag) is the feature that justifies 5s — but **spike it first**. If 270M can't chain tools, you need to know on day 1, not day 4.

---

## The One Thing That Moves All Four Scores

**Build the multi-turn chaining scenario and make it visible.** Three isolated single-turn queries are not enough. One scenario where tool output feeds the next call — printed step-by-step — proves: (1) it works reliably (Functionality), (2) routing happens mid-chain (Architecture), (3) real agentic behavior (Agentic), (4) reasoning on-device in under a second (Theme). That one feature justifies 5s across the board more than any other single addition.

---

## Judge Scoring Dimensions (What Blocks 5s)

| Dimension | Gap | Key Fix |
|-----------|-----|---------|
| **Functionality** | Stub fallback = canned responses; judges want flawless execution | Pre-flight script, health endpoint, singleton warmup, demo video backup |
| **Architecture** | Static regex routing; judges want dynamic escalation | Confidence-based escalation, latency-aware routing, connectivity probe, Scenario 5 (visible escalation) |
| **Agentic** | Single-turn only; judges want chaining, memory, reasoning | Multi-turn tool chaining (evaluate→check→flag), session memory, suggest_correction tool |
| **Theme** | Never articulates why local-first matters for welding | Privacy narrative, latency comparison, offline-first banner, --compare mode |

---

## Critical Decisions

- **Cactus path:** Copy `cactus/` from FunctionGemma repo into `backend/`. Use `os.path.dirname(os.path.abspath(__file__))` in `function_gemma.py` — works when imported as module. Cactus has compiled C/C++ extensions; `ls` is insufficient; real test is import succeeding.
- **Interrogative gate:** Route to cloud when: interrogative marker ("why", "explain", "improve", etc.) AND no measurement context. Measurement = `\d+\s*(?:V|A|°|degrees|volts|amps)` — not raw digits (WS-042, score 41 would wrongly trigger on-device).
- **Session ID:** Recovery targets `WS-\d+` only.
- **Cloud errors:** Return 200 with `{ source: "cloud_error", error: "..." }` — not 503.
- **Tool execution:** Return parsed `function_calls` only. No DB lookups.
- **Parameter enum:** `check_parameter_threshold` must have `parameter` as enum `["voltage","current","angle"]` — constrains 270M, prevents hallucinated param names.
- **Router pattern:** Match `predictions_router` — `APIRouter(prefix="/api/ai")`, `app.include_router(ai_router)` with no app prefix.
- **Async:** Wrap `generate_hybrid` in `asyncio.run_in_executor` — Cactus blocks; two concurrent requests would freeze backend.
- **Normalize source:** All on-device variants (empty, best-effort) → `source: "on-device"` — done **inside generate_hybrid**, not the route.
- **Offline fallback:** `--offline` means **no network** — bypass cloud for all scenarios. **Specify canned response:** Offline + coaching query must NOT return `{"source": "on-device", "function_calls": [], "text": ""}` — judges see blank and think it's broken. Return `{"source": "offline", "text": "Cloud coaching unavailable offline. Welding shop floors may lack connectivity — this is expected behavior."}` — turns limitation into feature demonstration.
- **Routing:** Single decision tree, single implementation. Steps 5b and 9 are one function — see diagram below.

---

## Routing Decision Tree (Single Implementation)

```
Query
  │
  ├─► interrogative gate (marker + no measurement) ─► cloud
  │
  └─► on-device
        │
        ├─► Cactus inference
        │
        └─► validation
              │
              ├─► valid ─► return
              │
              └─► invalid ─► escalate to cloud ─► return { source: "on-device→cloud", escalation_reason }
```

**Implement as one function.** Pre-inference gate and post-inference escalation are not separate steps — they are two branches of the same routing logic.

---

## Five Demo Scenarios (Complete Picture)

**Total runtime under 2 minutes. No UI.** Judges see on-device speed, cloud quality, intelligent routing, real agentic chaining, graceful degradation, and a privacy story.

| # | What it proves | Query | Expected | Where defined |
|---|----------------|-------|----------|---------------|
| **1** | On-device speed | "voltage is 28V, range 18-24" | source=on-device, check_parameter_threshold | Step 4 verification, Step 9 E2E |
| **2** | On-device speed | "angle 52 degrees, max 45" | source=on-device, check_parameter_threshold | Step 4 verification, Step 9 E2E |
| **3** | Cloud quality + intelligent routing | "session WS-042 scored 41, why?" | source=cloud, `text` has coaching | Step 5, Step 9 (interrogative gate) |
| **4** | Real agentic chaining | "Analyze session WS-042 — check score, then parameters, then flag any issues" | evaluate→check→flag, step-by-step printed | Step 4b |
| **5** | Graceful degradation | Query that fails validation (e.g. hallucinated param) | source=on-device→cloud, escalation_reason visible | Step 9 |

**Privacy story:** Step 6b — for every scenario, print `[ON-DEVICE] Sensor data never left the device.` or `[CLOUD] Anonymized query only — no raw sensor values transmitted.`

**Offline fallback:** `--offline` → Scenario 3 returns canned `{"source":"offline","text":"Cloud coaching unavailable offline..."}` — graceful degradation when wifi fails.

---

## Step Order (Risk-Driven: Spike Hardest First)

**Day-0 → Spike 4b → 1 → 2 → 6 → 4 → 3 → 3b → 5 → 8 (routing) → 6b → 7 → 9 → 10**

- **Day-0:** Cactus import on demo machine — **blocker**
- **Spike 4b:** Multi-turn chaining with stubs. Does 270M actually chain tools? What's latency for 3 sequential calls? **Fail fast on the hardest thing.** If 270M can't chain, know on day 1.
- **1–2, 6:** Foundation + demo skeleton
- **4, 3, 3b:** Engine + singleton warmup + reactive cloud fallback
- **5:** Cloud implementation
- **8 (routing):** Unified interrogative gate + escalation — one diagram, one function (replaces old 5b + 9)
- **6b:** Privacy/latency (dynamic multiplier only)
- **7, 9, 10:** API + E2E + health

---

## Tasks

**Execute in risk-driven order.** Day-0 and Spike 4b come first. If either fails, the plan is blocked or must pivot.

### Phase 0 — Day-0 + Empirical Spike (Before Any Other Code)

**Day-0:** Run `python -c "import sys; sys.path.insert(0,'backend/cactus/python/src'); from cactus import cactus_init; print('OK')"` on the **exact machine** you will demo on. No → blocked.

---

**Spike: 20-line empirical test.** Answers one binary question with minimum code in minimum time.

**Core assumption:** FunctionGemma 270M will reliably produce parseable tool calls for welding queries. That assumption is never tested until halfway through implementation. Test it first.

**Test 1 — Single-turn validity (run 10 times):**
```python
# ~20 lines. Call real Cactus. Send exactly:
query = "voltage is 28V, acceptable range 18-24V"
# Check if output contains check_parameter_threshold with parameter=voltage
# Record: valid parseable tool call? Y/N
# Run 10 times. Success rate = ?
```
**Decision tree (no ambiguity):**

| Single-turn rate | Multi-turn | Action |
|------------------|------------|--------|
| **≥80%** | Y | Proceed as planned |
| **50–79%** | Y | Proceed on-device with escalation as safety net; ~30% of queries will escalate to cloud |
| **50–79%** | N | Single-turn only; skip Step 4b |
| **<50%** | — | On-device path unreliable; route all tool calls through cloud; on-device becomes fallback, not primary |

Without this, whoever runs the spike doesn't know what to do. They'll guess.

**Test 2 — Multi-turn (10 minutes):** Manually construct `[user_msg, assistant_tool_call, tool_result]`. Call Cactus once. Coherent second call? Y/N.

**Record the numbers.** Document: single-turn rate, multi-turn Y/N, decision taken.

---

### Phase 1 — Pre-Flight & Foundation

---

- [ ] 🟥 **Step 0: Create check_env.py pre-flight script**

  **Subtasks:**
  - [ ] 🟥 Script tests: Cactus import, weights path exists, GEMINI_API_KEY set, `POST /api/ai/analyze` returns 200, two concurrent POSTs both complete, all 5 scenarios end-to-end
  - [ ] 🟥 Exit 0 if all pass; exit 1 with clear failure message if any fail
  - [ ] 🟥 **Run the night before, not on stage.** Catches Cactus failures before demo day.

  **✓ Verification Test:** `python backend/check_env.py` — all checks pass or fail with actionable message.

---

- [ ] 🟥 **Step 1: Copy Cactus and verify import**

  **Subtasks:**
  - [ ] 🟥 **Before anything else:** Check FunctionGemma repo for `requirements.txt`, `pip install -e .`, or `setup.sh`. Hackathon repo — there may be no clean setup. Cactus is C++ with pybind11-generated Python bindings; .so files may be compiled for a specific macOS/ARM combo. If the demo machine is a different Mac than the build machine, binaries may not work.
  - [ ] 🟥 Copy `cactus/` folder from FunctionGemma repo into `backend/cactus/`
  - [ ] 🟥 Shared libraries: if import fails with "image not found" or dylib errors, set `DYLD_LIBRARY_PATH` to include cactus lib dir
  - [ ] 🟥 **Real verification:** `from cactus import cactus_init` (or actual entry module per v2) succeeds — not `ls`
  - [ ] 🟥 **Stub fallback:** If import fails after all setup attempts, stub `generate_cactus` (or equivalent) to return a hardcoded on-device response. Demo must survive Step 1 failure. A stubbed on-device path beats a broken demo.

  **✓ Verification Test:**

  **Action:** `cd backend && python -c "import sys; sys.path.insert(0, 'cactus/python/src'); from cactus import cactus_init; print('OK')"` — adjust module name to match v2 Cactus API.

  **Expected Result:** Prints "OK"; no ModuleNotFoundError, no symbol/ABI errors from compiled extensions.

  **Pass Criteria:** Cactus imports, or stub is in place and demo runs with canned on-device.

  **Common Failures & Fixes:**
  - **If ModuleNotFoundError:** Check cactus/python/src; run `pip install -e .` if repo provides it
  - **If native extension fails (wrong Mac, wrong ABI):** Implement stub fallback; demo continues with hardcoded responses

---

- [ ] 🟥 **Step 2: Create warp_tools.py with enum constraint**

  **Subtasks:**
  - [ ] 🟥 Define `WARP_TOOLS` with 3 tools: `check_parameter_threshold`, `evaluate_session_score`, `flag_anomaly`
  - [ ] 🟥 **Critical:** `check_parameter_threshold` → `parameter` must be JSON schema enum: `{"type":"string","enum":["voltage","current","angle"]}` — not freeform string.
  - [ ] 🟥 **Post-inference enum check:** Cactus may ignore the enum field (no constrained decoding). If 270M hallucinates "wire_feed" instead of "voltage", `_recover_arguments` won't fix it and validation would pass. In `_validate_tool_call`, reject any `check_parameter_threshold` call where `parameter` is not in `["voltage","current","angle"]` — treat as invalid, fall through to cloud.

  **Code snippet (parameter field):**

  ```python
  "parameter": {
      "type": "string",
      "enum": ["voltage", "current", "angle"],
      "description": "Parameter name: voltage, current, or angle."
  },
  ```

  **Code snippet (_validate_tool_call):**

  ```python
  ALLOWED_PARAMETERS = frozenset({"voltage", "current", "angle"})
  # For check_parameter_threshold, if args.get("parameter") not in ALLOWED_PARAMETERS: return False
  ```

  **✓ Verification Test:**

  **Action:** `cd backend && python -c "from warp_tools import WARP_TOOLS; p=WARP_TOOLS[0]['parameters']['properties']['parameter']; assert 'enum' in p; print(p['enum'])"`

  **Expected Result:** Prints `['voltage', 'current', 'angle']`

  **Pass Criteria:** `parameter` has enum constraint; `_validate_tool_call` rejects invalid parameter values

---

- [ ] 🟥 **Step 6: Create weld_demo.py (early — demo-first)** — *Why it matters: error handling, path robustness, offline fallback*

  **Context:** Get demo script green before API. Must work from both `python backend/weld_demo.py` (project root) and `cd backend && python weld_demo.py`. Use `__file__`-relative path. **Import at module load triggers Cactus init** — if Step 1 not done, demo crashes with raw traceback. Wrap import in try/except. **Offline fallback:** `--offline` = no network for all scenarios. Pass offline to `generate_hybrid`. **Canned response for cloud-bound queries when offline:** Return `{"source": "offline", "text": "Cloud coaching unavailable offline. Welding shop floors may lack connectivity — this is expected behavior."}` — not blank, not fake coaching. Turns limitation into feature.

  **Code snippet:**

  ```python
  import argparse
  import os
  import sys

  _DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
  if _DEMO_DIR not in sys.path:
      sys.path.insert(0, _DEMO_DIR)

  try:
      from warp_tools import WARP_TOOLS
      from function_gemma import generate_hybrid
  except Exception as e:
      print("Cactus not available — run Step 1 first.")
      print(f"Error: {e}")
      sys.exit(1)

  def run(label, query, offline=False):
      result = generate_hybrid([{"role": "user", "content": query}], WARP_TOOLS, offline=offline)
      print(f"  SOURCE : {result.get('source')}")
      print(f"  TIME   : {result.get('total_time_ms', 0):.0f}ms")
      if result.get("text"):
          t = result['text']
          print(f"  TEXT   : {t[:200]}{'...' if len(t) > 200 else ''}")  # Cloud coaching
      for call in result.get("function_calls", []):
          print(f"  TOOL   : {call['name']}")
          print(f"  ARGS   : {call.get('arguments', {})}")
      if not result.get("function_calls") and not result.get("text"):
          print("  TOOL   : (none)")
  ```

  **What it does:** try/except on import. `--offline` passed to `generate_hybrid` — engine skips all Gemini calls, returns canned responses for cloud-bound scenarios. No keyword check in demo.

  **Why this approach:** Offline = "no network"; works regardless of query wording.

  **Assumptions:** `generate_hybrid` accepts `offline` param; when True, never calls Gemini.

  **✓ Verification Test:**

  **Action:** (1) With Cactus broken/missing: run demo → expect "Cactus not available" and exit 1. (2) Both cwds run. (3) `weld_demo.py --offline` — **all** scenarios run with no network; Scenario 3 shows canned cloud. (4) Change Scenario 3 query to "what should the welder improve?" — offline still works, no network call.

  **Pass Criteria:** Import failure graceful; both cwds work; --offline = zero network for any query

---

### Phase 2 — On-Device Engine (Critical Path)

---

- [ ] 🟥 **Step 4: Adapt welding prompt, recovery, validation** — *Most critical — determines if on-device works*

  **Context:** 270M is tiny and prompt-sensitive. **Hidden blocker:** You don't know what v2 examples look like. v2 may use a completely different structure than what 270M was fine-tuned on. You could write examples that look right but don't match the training distribution. The unit test for `_recover_arguments` tests the regex, not whether the model actually calls the right tool.

  **Real test (empirical, not unit-testable):** Send your 3 demo queries to the model verbatim. Record what tool calls come back. Adjust examples until they consistently match. Run each query 3–5 times before moving on.

  **Subtasks:**
  - [ ] 🟥 Replace **only the examples** in `_BASE_SYSTEM_PROMPT` with welding ones. Keep v2 structure if known; otherwise match format from Phase 0 spike output.
  - [ ] 🟥 Replace `_TOOL_ACTION_VERBS` with welding verbs (check, flag, evaluate)
  - [ ] 🟥 Replace `_recover_arguments` — recover numeric sensor values + `WS-\d+` session IDs
  - [ ] 🟥 **Range regex — two separate patterns:** Use `r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)'` and `r'(\d+\.?\d*)\s+to\s+(\d+\.?\d*)'` — never `[-–to]+` (character class bug).
  - [ ] 🟥 Simplify `_validate_tool_call` — remove hour/minute guards; add post-inference enum check (Step 2)

  **✓ Verification Test (empirical):**

  **Action:** Send "voltage is 28V, range 18-24", "angle 52 degrees, max 45", "session WS-042 scored 41" to the model. Record tool calls. Adjust prompt until they match. Unit test `_recover_arguments` separately for regex.

  **Pass Criteria:** All 3 demo queries produce correct tool calls; regex handles "18 to 24", "18-24", "18–24"

---

- [ ] 🟥 **Step 3: Create function_gemma.py — engine core** — *Why it matters: path resolution, blocking, Cactus singleton, source normalization*

  **Context:** Path resolution via `__file__` works when module is imported. Cactus inference is synchronous; wrap in `run_in_executor` for route (Step 7). **Singleton with warmup:** Initialize Cactus once at module load; run a dummy inference call to warm the model. First real call is never cold. Eliminates hang-on-second-call risk entirely. **Source normalization:** Inside `generate_hybrid`, before any return: if `source.startswith("on-device")` → set `source = "on-device"`.

  **Code snippet (path setup + singleton):**

  ```python
  import os
  import sys
  import threading

  _BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
  _CACTUS_SRC = os.path.join(_BACKEND_DIR, "cactus", "python", "src")
  _WEIGHTS_PATH = os.path.join(_BACKEND_DIR, "cactus", "weights", "functiongemma-270m-it")

  if _CACTUS_SRC not in sys.path:
      sys.path.insert(0, _CACTUS_SRC)

  # Singleton: init once at load, warmup with dummy inference. Thread-safe: two
  # concurrent requests before warmup would both call cactus_init. Use a lock.
  _cactus_initialized = False
  _cactus_lock = threading.Lock()
  def _ensure_cactus_warm():
      global _cactus_initialized
      if _cactus_initialized:
          return
      with _cactus_lock:
          if _cactus_initialized:
              return
          cactus_init(...)  # or equivalent
          _run_dummy_inference()  # warm model
          _cactus_initialized = True
  ```

  **✓ Verification Test:** (1) Single call works. (2) Run full weld_demo (all 5 scenarios) — no hang. (3) Response has normalized source.

  **Pass Criteria:** Works from both cwds; 3 sequential calls succeed; singleton eliminates cold-start hang

  **Assumptions:** function_gemma.py is always imported, never exec'd as main.

- [ ] 🟥 **Step 3b: Reactive cloud fallback (no proactive probe)** — *Dynamic routing*

  **Context:** Proactive "ping Gemini at startup" is wrong: blocks startup, race conditions (probe says up, wifi drops before real call), cost (billable API call every startup). **Right design:** Optimistic cloud attempt with fast timeout (2s); on failure, immediate fallback to on-device. Cache result for 30 seconds. Don't probe proactively — fail fast reactively.

  **Subtasks:**
  - [ ] 🟥 When cloud path is chosen: attempt Gemini with **2s timeout**. **Critical:** The Gemini SDK default timeout is 30+ seconds. You must explicitly set it. Without this, reactive fallback never triggers — the thread hangs. Set a 2-second timeout — verify against installed SDK version. (Confident wrong guidance is worse than honest uncertainty.)
  - [ ] 🟥 On timeout/failure: fall back to on-device (or return cloud_error if offline). Cache `_cloud_available` for 30s after success.
  - [ ] 🟥 Add `latency_ms` to every response.

  **Pass Criteria:** Timeout explicitly set; reactive fallback triggers within 2s; `latency_ms` in response

---

- [ ] 🟥 **Step 4b: Multi-turn tool chaining**

  **Hard gate — do not start until spike is complete:**
  - [ ] Spike results documented: single-turn ≥80%, multi-turn Y/N. Gate is hard, not advisory. In a hackathon with parallel work, someone will start Step 4b while someone else runs the spike unless the plan forbids it.

  **Context:** Phase 0 spike must show: (1) single-turn ≥80% valid, (2) multi-turn produces coherent second call. If either fails, skip or pivot per decision tree. This step implements the full loop only after the model is proven capable.

  **Architecture (specify before coding):**
  - **Message history format:** Match format model was trained on (v2). Typically: `[{role, content}, {role, content, tool_calls?}, {role, content, tool_call_id?}, ...]`.
  - **Termination condition:** (a) No tool call returned; (b) Max steps (e.g. 5); (c) Explicit "done". Document which.
  - **Error handling mid-chain:** Step 2 fails after step 1 — partial result, retry, or escalate. Specify.
  - **Latency budget:** 3× Cactus = 1.5s–6s. If >6s, consider cloud for chained.

  **Subtasks:**
  - [ ] 🟥 Implement `run_chained` loop; append tool results to messages; call Cactus per step.
  - [ ] 🟥 Add Scenario 4: "Analyze session WS-042 — check score, then parameters, then flag any issues." Print step-by-step.
  - [ ] 🟥 Optional: `session_context`, `suggest_correction` tool.

  **Pass Criteria:** Scenario 4 runs; step-by-step output; spike numbers documented

---

- [ ] 🟥 **Step 5: Implement generate_cloud with Gemini** — *Copy from v2, fix welding prompt, extract text*

  **Context:** Copy `generate_cloud` from v2. **Critical:** v2's `system_instruction` says "Count every distinct action — make exactly that many tool calls." Wrong for Scenario 3 — replace with welding coach instruction. **Response shape:** v2 parses `candidate.content.parts` for `part.function_call` only. For Scenario 3 (open-ended coaching), Gemini returns **text**, not a function call. v2 returns `{"function_calls": [], "total_time_ms": ...}` — judges see SOURCE: cloud, TOOL: (none) and think it failed. **Extract `part.text`** from the response and include in return dict as `"text"` field. Demo prints coaching text; judges see the value.

  **Subtasks:**
  - [ ] 🟥 **Pre-step:** Add `google-generativeai>=0.8.0` to WarpSense `backend/requirements.txt`.
  - [ ] 🟥 **v2 provenance (establish before copying):** What is v2? Who wrote it? When was it last run? Is it tested? If v2 is hackathon starter code and nobody has verified it against the current Gemini API version, you're inheriting unknown bugs. Document provenance. Verify: `parse_tool_calls` handles empty `parts` array; extracts `part.text` (not just `part.function_call`). Run v2's generate_cloud once against live Gemini before copying.
  - [ ] 🟥 Replace Gemini `system_instruction` with:
    > "You are a welding quality coach. For analytical questions (why, how, explain, improve), respond with structured advice. For tool calls, use the provided schema."
  - [ ] 🟥 Extract both `part.function_call` and `part.text` from `candidate.content.parts`. Return `{"function_calls": [...], "text": "...", "total_time_ms": ...}`. When Gemini returns text only, `text` has the coaching response; `function_calls` may be empty.
  - [ ] 🟥 Wrap in try/except in `generate_hybrid`; return `cloud_error` on any exception

  **✓ Verification Test:**

  **Action:** With GEMINI_API_KEY set, call with "why is the score low?". Expect `source: cloud`, `text` field with welding-relevant coaching (not empty). Demo prints the text. Unset key → `cloud_error`.

  **Pass Criteria:** Cloud returns `text` for coaching queries; demo shows coaching content; google-generativeai in requirements.txt

---

- [ ] 🟥 **Step 6b: Privacy narrative, latency, offline banner** — *Theme alignment*

  **Subtasks:**
  - [ ] 🟥 **Privacy narrative:** For every scenario, print `[ON-DEVICE] Sensor data never left the device.` or `[CLOUD] Anonymized query only — no raw sensor values transmitted.`
  - [ ] 🟥 **Latency comparison:** Compute ratio dynamically from actual `total_time_ms`. If on-device < cloud, print `[Nx faster on-device]` where N = cloud_ms / on_device_ms. **Never hardcode 5.3x.** If a judge asks "how did you measure that?" — you must have measured it.
  - [ ] 🟥 **Offline banner:** When `--offline`, print banner: "OFFLINE MODE — Zero network calls. Welding shop floors have poor connectivity."
  - [ ] 🟥 **--compare mode (decide before building):** Don't build and then verify. **Decide upfront:** Pick one query where cloud is demonstrably better. "Why is my score low?" — real Gemini coaching text vs on-device returning empty (no tool call). That's your --compare query. If you can't name it now, cut the feature. Building --compare and then discovering cloud doesn't win = wasted implementation time.

  **Pass Criteria:** Privacy/latency visible; multiplier from real measurements; --compare query decided before implementation (or feature cut)

---

### Phase 3 — API Route & E2E

---

- [ ] 🟥 **Step 7: Create routes/ai.py** — *Why it matters: validation bug, async*

  **Context:** Validation must be correct. `if not (body.query or body.query.strip())` is wrong: empty string short-circuits `or` and never calls `.strip()`; "   " is truthy so we never reject. Use `if not body.query or not body.query.strip()`. **Source normalization lives in generate_hybrid** (Step 3), not here — so weld_demo and API both get normalized output.

  **Code snippet:**

  ```python
  import asyncio
  from fastapi import APIRouter, HTTPException
  from pydantic import BaseModel

  from function_gemma import generate_hybrid
  from warp_tools import WARP_TOOLS

  router = APIRouter(prefix="/api/ai", tags=["ai"])

  class AnalyzeRequest(BaseModel):
      query: str

  @router.post("/analyze")
  async def post_analyze(body: AnalyzeRequest):
      if not body.query or not body.query.strip():
          raise HTTPException(status_code=400, detail="query is required")
      loop = asyncio.get_running_loop()
      result = await loop.run_in_executor(
          None,
          lambda: generate_hybrid(
              [{"role": "user", "content": body.query.strip()}],
              WARP_TOOLS,
          ),
      )
      return result
  ```

  **What it does:** Correct validation; `run_in_executor` prevents blocking. No source normalization — engine does it.

  **Why this approach:** Two judges hitting endpoint simultaneously won't freeze backend. Validation catches both "" and "   ".

  **✓ Verification Test:**

  **Action:** (1) POST with `{"query":""}` → 400. (2) POST with `{"query":"   "}` → 400. (3) POST with `{"query":"voltage 28V"}` → 200, source in response. (4) **Concurrent:** Run two `curl -X POST ... -d '{"query":"angle 52"}'` in parallel (e.g. `curl ... & curl ... & wait`). Both must return 200; neither should block the other.

  **Pass Criteria:** Empty/whitespace rejected; valid query returns 200; two parallel POSTs both complete (no hang)

---

- [ ] 🟥 **Step 8: Register AI router in main.py** — *Consistent with existing pattern*

  **Context:** Match `predictions_router`: router has full prefix, app adds none.

  **Code snippet:**

  ```python
  from routes.ai import router as ai_router

  app.include_router(ai_router)
  ```

  **What it does:** Mounts POST /api/ai/analyze (router already has prefix="/api/ai").

  **Why this approach:** Consistent with predictions_router (prefix="/api/sessions"), welders_router, etc.

  **✓ Verification Test:**

  **Action:** Start backend; `curl -X POST http://localhost:8000/api/ai/analyze -H "Content-Type: application/json" -d '{"query":"angle 52"}'`

  **Expected Result:** 200; JSON with source, function_calls

  **Pass Criteria:** /api/ai/analyze responds

---

- [ ] 🟥 **Step 9: Unified routing (interrogative gate + escalation)** — *One diagram, one function*

  **Context:** This step implements the full routing decision tree. Pre-inference gate and post-inference escalation are **one function**, not two separate mechanisms. See diagram at top of plan.

  **Subtasks:**
  - [ ] 🟥 **Branch 1 — Interrogative gate (before Cactus):** If `_is_interrogative(last_msg)` → route to cloud. Use measurement pattern `\d+\s*(?:V|A|°|degrees|volts|amps)` — not raw digits. "session WS-042 scored 41, why?" → no measurement → cloud. "voltage 28V range 18-24" → has measurement → on-device.
  - [ ] 🟥 **Branch 2 — On-device:** Run Cactus inference.
  - [ ] 🟥 **Branch 3 — Escalation (after validation):** If `_validate_tool_call` fails OR no tool call when one expected → escalate to cloud. Return `{"source": "on-device→cloud", "escalation_reason": "enum_validation_failed"}`. Don't return empty.
  - [ ] 🟥 Add escalation scenario to weld_demo: query that starts on-device, fails validation, escalates. Print `SOURCE : on-device→cloud (escalated: enum validation failed)`.
  - [ ] 🟥 Run full E2E: Scenario 1 → on-device, Scenario 2 → on-device, Scenario 3 → cloud, Scenario 4 → chained, Scenario 5 (escalation) → on-device→cloud.

  **Code snippet (unified routing):**

  ```python
  def _route(messages, tools):
      last_msg = (messages[-1].get("content") or "") if messages else ""
      if _is_interrogative(last_msg):
          return _cloud_fallback(messages, tools)
      result = _on_device_inference(messages, tools)
      if not _validate_tool_call(result.get("function_calls", []), tools):
          return _escalate_to_cloud(messages, tools, result, reason="validation_failed")
      return result
  ```

  **Pass Criteria:** Single routing function; interrogative gate + escalation both work; escalation visible in demo

---

- [ ] 🟥 **Step 10: Add GET /api/ai/health endpoint** — *Judges trust systems they can probe*

  **Subtasks:**
  - [ ] 🟥 `GET /api/ai/health` returns `{"cactus": "ok"|"error", "gemini": "ok"|"key_configured"|"error"|"unconfigured", "model_loaded": true|false}`.
  - [ ] 🟥 **Gemini honesty:** If you only check key presence, do NOT return `"gemini": "ok"`. Key can be set but expired/invalid — health says ok, first Scenario 3 fails. That's false confidence. Either: (a) do a real lightweight Gemini call and report actual connectivity, or (b) be honest: `"gemini": "key_configured"` — you haven't verified it works.
  - [ ] 🟥 Cactus: check import + singleton initialized.

  **Pass Criteria:** Health endpoint honest about Gemini state; no false "ok" when unverified

---

## Demo Day Backup Checklist

| Backup | Purpose |
|--------|---------|
| **check_env.py** | Run night before; catch failures early |
| **Phone hotspot** | Pre-configured; don't rely on hackathon wifi |
| **Demo video** | 90-second screen recording of all scenarios. If anything breaks live, play the video. Judges penalize broken demos, not backup videos. |
| **--offline** | Zero network when wifi fails |
| **Screenshot** | Successful Scenario 3 with coaching text |

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 0** | check_env.py | Run `python backend/check_env.py` night before demo | ⬜ |
| **Phase 1** | google-generativeai in requirements.txt | Add `google-generativeai>=0.8.0` | ⬜ |
| | FunctionGemma setup | Run pip install -e . or setup.sh from repo first | ⬜ |
| | Cactus imports | `from cactus import cactus_init` succeeds — or stub in place | ⬜ |
| | v2 source available | Have generate_cloud, parse_tool_calls from v2 | ⬜ |
| **Phase 2** | Singleton warmup | Cactus init once + dummy inference; thread-safe (Lock); no hang on 2nd call | ⬜ |
| | Recovery regex | Unit test "18 to 24", "18-24", "18–24" — two patterns | ⬜ |
| | Multi-turn chaining | Scenario 4 runs; step-by-step output | ⬜ |
| **Phase 3** | GEMINI_API_KEY | Optional; needed for cloud | ⬜ |
| | Health endpoint | GET /api/ai/health returns cactus, gemini, model_loaded | ⬜ |
| | Demo video | 90-second recording; backup if live fails | ⬜ |
| | Phone hotspot | Pre-configured for Gemini | ⬜ |

---

## Risk Heatmap

**Step 1 has 70% failure probability.** A senior engineer reading this should be alarmed. Better-than-even chance the entire foundation doesn't work. Everything after Step 1 is speculative until Cactus runs on target hardware.

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| **Day-0** | 🔴 **Blocker** | Cactus never imports on demo machine | Run import test on exact machine before any code |
| Step 1 | 🔴 **70%** | Cactus binaries wrong Mac/ABI; stub = canned responses | Day-0 check; check_env.py night before |
| Spike 4b | 🟡 **50%** | 270M cannot chain tools; multi-turn fails | Spike on day 1; don't build polish around broken core |
| Step 4 | 🟡 **50%** | Range regex character class bug | Unit test both patterns before integration |
| Step 9 | 🟡 **25%** | Interrogative gate wrong — Scenario 3 on-device | Use measurement pattern; Proof Checkpoint |
| Demo day | 🟡 **30%** | Wifi drops; Cactus fails on judge machine | check_env.py; demo video; hotspot |

---

## Proof Checkpoints (Evidence It Works)

The plan describes what to build. Proof checkpoints prove the core assumption works. Each is **testable before the next phase**.

| Checkpoint | When | How to Prove |
|------------|------|--------------|
| **Day-0** | Before any code | Cactus imports on demo machine |
| **Empirical spike** | Day 1 | 20-line test: "voltage 28V, range 18-24" → Cactus → check for check_parameter_threshold. Run 10×. Success rate ≥80%? Multi-turn: manual message with tool result → Cactus once → coherent second call? Record numbers. |
| **Step 1** | After Cactus copy | Import succeeds OR stub in place |
| **Step 4** | Before Step 3 | Send 3 demo queries to model; record tool calls; adjust until consistent. Regex unit test separately. |
| **Step 9** | Before polish | POST "session WS-042 scored 41, why?" → cloud; POST "voltage 28V" → on-device; escalation → on-device→cloud |
| **Final gate** | Before demo | All 5 scenarios run on demo machine, no code changes |

---

## Success Criteria

| Priority | Feature | Target Behavior | Verification | Milestone |
|----------|---------|----------------|--------------|-----------|
| **P0** | Day-0 | Cactus imports on demo machine | Import test | Blocker |
| **P0** | Empirical spike | Single-turn ≥80% valid; multi-turn coherent 2nd call (or documented) | 20-line test, 10 runs; manual tool-result test | Day 1 |
| **P0** | On-device | "voltage 28V range 18-24" → source=on-device | POST /api/ai/analyze | Step 9 |
| **P0** | Cloud | "session WS-042 scored 41, why?" → source=cloud, `text` has coaching | POST; demo prints text | Step 9 |
| **P0** | Escalation | On-device fails → escalates; source="on-device→cloud" visible | weld_demo escalation scenario | Step 9 |
| **P0** | Final gate | All 5 scenarios on demo machine, no code changes | Full E2E run | CTO approval |
| **P1** | Pre-flight | check_env.py passes night before | `python backend/check_env.py` | Night before |
| **P1** | Health | cactus, gemini (key_configured or ok), model_loaded — honest, no false "ok" | Judges hit before demo | Step 10 |
| **P1** | Multi-turn | evaluate→check→flag; step-by-step printed | weld_demo Scenario 4 | Step 4b |
| **P1** | Offline | `--offline` → zero network; coaching query returns offline message, not blank | `{"source":"offline","text":"Cloud coaching unavailable offline..."}` | Step 6 |
| **P1** | Concurrent | Two parallel POSTs both return 200 | Step 7 verification | Step 7 |
| **P2** | Privacy/latency | [ON-DEVICE]/[CLOUD] narrative; multiplier from real ms | weld_demo output | Step 6b |
| **P2** | --compare | Query decided upfront ("Why is my score low?") or feature cut | weld_demo --compare | Step 6b (optional) |

**P0 = demo fails without it. P1 = score impact. P2 = bonus. Cut P2 first if time runs out.**

---

## Priority Order for Implementation

1. **Day-0:** Cactus import on demo machine. If no, plan is blocked.
2. **Spike 4b:** Multi-turn chaining with stubs. Does 270M chain? What's 3-step latency? Fail fast on the hardest thing.
3. **Singleton warmup (Step 3):** Eliminates hang risk.
4. **Unified routing (Step 9):** Interrogative gate + escalation — one function.
5. **check_env.py (Step 0):** Run night before.
6. **Health endpoint (Step 10):** Judges probe before trusting.

---

## CTO Approval Checklist

**Everything else is preparatory. One gate counts.**

- [ ] **Run all 5 demo scenarios end-to-end on the exact demo machine with no code changes.** That's the only approval gate that matters. A plan that passes 7 checklist items but has never been run on the demo machine in its entirety is not approved.

**Preparatory items:**
- [ ] Day-0: Cactus imports on demo machine
- [ ] Empirical spike: single-turn ≥80% valid; multi-turn coherent second call (or documented failure)
- [ ] Routing: single diagram, single function
- [ ] Connectivity: reactive fallback with explicit 2s timeout (SDK parameter set)
- [ ] Latency multiplier: computed from real measurements
- [ ] --compare: query decided upfront (or feature cut)
- [ ] v2 provenance: established before copying; run against live Gemini once
- [ ] Offline canned response: specified and implemented
- [ ] Health endpoint: honest about Gemini (key_configured vs ok)

---

## Three Things Required Before Execution

1. **20-line empirical test (Phase 0):** Does 270M produce valid tool calls for exact queries? At what rate? Can it do multi-turn? Run before anything else. Record numbers. (See Phase 0.)
2. **Explicit Gemini timeout (Step 3b):** SDK parameter for 2s timeout — without it, reactive fallback silently doesn't work. (See Step 3b.)
3. **Final CTO gate:** Run all 5 scenarios on demo machine, no code changes. Only gate that counts. (See CTO Approval Checklist.)

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes.**
