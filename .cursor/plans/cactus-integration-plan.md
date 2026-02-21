# Cactus Integration Plan — FunctionGemma 270M into WarpSense

**Overall Progress:** `0%` (0/5 steps)

## TLDR

Replace the stub on-device path in `function_gemma.py` with real Cactus inference. The stub-based system (warp_tools, weld_demo, routes, check_env) is already working. This plan adds the Cactus folder, empirical spike, welding-specific prompts/recovery, and verification.

---

## What Already Exists

| File | Status | Purpose |
|------|--------|---------|
| `backend/warp_tools.py` | 🟩 Done | 3 welding tools, ALLOWED_PARAMETERS enum |
| `backend/function_gemma.py` | 🟨 Stub | generate_hybrid, _stub_on_device_response, _generate_cloud, routing |
| `backend/weld_demo.py` | 🟩 Done | 5 scenarios, --offline, privacy narrative |
| `backend/routes/ai.py` | 🟩 Done | POST /api/ai/analyze, GET /api/ai/health |
| `backend/check_env.py` | 🟩 Done | Pre-flight verification |
| `backend/main.py` | 🟩 Done | ai_router registered |

## What Is Missing

- Cactus folder (C++ runtime + Python bindings + weights) from FunctionGemma repo
- Real inference replacing `_stub_on_device_response`
- Welding-specific argument recovery (range regex, session ID, sensor values)
- v2 API alignment: `cactus_init`, `cactus_complete` (or equivalent per repo)

---

## Ownership & Time Estimates

| Step | Owner | Time (clean) | Time (if blocked) |
|------|-------|--------------|-------------------|
| **Step 1** | Engineer with repo access | 30 min | 2 hours (ABI mismatch → recompile on demo machine) |
| **Step 2** | Same engineer (spike blocks Step 3) | 20 min | N/A — spike is the gate |
| **Step 3** | Backend engineer | 45 min | 1 hour (API mismatch → grep + adapt) |
| **Step 4** | Backend engineer | 30 min | 45 min (field name mismatch → verify warp_tools first) |
| **Step 5** | Any | 15 min | N/A |

**Spike owner:** Whoever runs Step 1. Spike must run before Step 3 — no code in function_gemma until spike numbers are documented.

---

## Critical Decisions

- **Cactus path:** `backend/cactus/` — use `__file__`-relative paths in function_gemma.py
- **Stub fallback:** If Cactus import fails, keep `_stub_on_device_response` — demo survives
- **Argument recovery:** Two regex patterns for range: `(\d+)\s*[-–]\s*(\d+)` and `(\d+)\s+to\s+(\d+)` — never character class `[-–to]+`
- **Parameter enum:** `check_parameter_threshold` → parameter must be in `["voltage","current","angle"]` — reject hallucinated values
- **Spike decision:** ≥80% → proceed; 50–79% → proceed with escalation; <50% → route all to cloud
- **Cloud timeout:** 2s via ThreadPoolExecutor — already in `_generate_cloud`

---

## Architecture (Data Flow)

```
weld_demo.py OR POST /api/ai/analyze
        │
        ▼
function_gemma.generate_hybrid(messages, tools, offline)
        │
        ├─► Interrogative gate (why/explain + no measurement?) ─► Gemini cloud
        │
        ├─► On-device path ─► Cactus inference (_infer_local)
        │         │
        │         ▼
        │   _validate_tool_call(result)
        │         ├─► valid ─► return {source: on-device, function_calls}
        │         └─► invalid ─► escalate to Gemini ─► {source: on-device→cloud}
        │
        └─► offline=True ─► canned offline response (no network)
```

---

## Tasks

### Phase 0 — Blocker + Spike

**Goal:** Cactus imports on demo machine; 270M produces valid welding tool calls at ≥80% rate.

- [ ] 🟥 **Step 1: Get the Cactus folder (Blocker)**

  **Context:** 70% failure probability. Cactus has compiled C++ extensions; wrong Mac/ABI = import fails. Everything else is blocked until this passes.

  **Subtasks:**
  - [ ] 🟥 Clone FunctionGemma repo: `git clone https://github.com/cactus-compute/function-gemma.git ~/function-gemma-repo`
  - [ ] 🟥 **First thing after cloning — API discovery (do not skip):** Run `grep -r 'def cactus_' ~/function-gemma-repo` (or equivalent). Document actual function names (cactus_init? cactus_infer? cactus_complete?). Update Step 3 code accordingly before writing any integration code. Who owns this: the engineer doing Step 1. When: before Step 3.
  - [ ] 🟥 Install Cactus deps (setup.sh, pyproject.toml, or requirements.txt per repo)
  - [ ] 🟥 Copy `cactus/` into `backend/cactus/` — ensure .so binaries present
  - [ ] 🟥 Run import test on **exact demo machine**

  **✓ Verification Test:**

  **Action:** From `backend/`: `python -c "import sys; sys.path.insert(0, 'cactus/python/src'); from cactus import cactus_init; print('OK')"`

  **Expected Result:** Prints "OK"; no ModuleNotFoundError, no dylib/ABI errors

  **How to Observe:** Terminal output; exit code 0

  **Pass Criteria:** Import succeeds; or stub remains and demo runs with canned responses

  **Common Failures & Fixes:**
  - **ModuleNotFoundError:** Check cactus/python/src; run `pip install -e .` if repo provides it
  - **dylib/ABI error:** Recompile on demo machine or keep stub
  - **Wrong path:** Verify _CACTUS_SRC in function_gemma.py matches repo layout

---

- [ ] 🟥 **Step 2: Empirical spike**

  **Owner:** Same engineer who completed Step 1. Spike blocks Step 3 — no integration code until numbers are documented.

  **Context:** Verify 270M produces parseable welding tool calls before investing in prompt tuning.

  **Subtasks:**
  - [ ] 🟥 Create `backend/spike_test.py`: call cactus_complete 10× with `"voltage is 28V, acceptable range 18-24V"`
  - [ ] 🟥 Record: valid check_parameter_threshold with parameter=voltage? Y/N per run
  - [ ] 🟥 Multi-turn: manual `[user_msg, assistant_tool_call, tool_result]` → coherent second call? Y/N
  - [ ] 🟥 Document: single-turn rate, multi-turn Y/N, decision per table

  **Decision table:**

  | Single-turn rate | Multi-turn | Action |
  |------------------|------------|--------|
  | ≥80% | Y | Proceed as planned |
  | 50–79% | Y | Proceed; escalation as safety net |
  | 50–79% | N | Single-turn only; skip Step 4b |
  | <50% | — | **In generate_hybrid: skip _infer_local entirely; call _generate_cloud directly for all queries.** On-device becomes fallback only when cloud fails. |

  **✓ Verification Test:**

  **Action:** Run `python backend/spike_test.py`; inspect output for 10 runs

  **Expected Result:** Success rate recorded; decision taken per table

  **Pass Criteria:** Spike complete; numbers documented; go/no-go decision

---

### Phase 1 — Adapt function_gemma.py

**Goal:** Real Cactus inference replaces stub; welding prompts and recovery in place.

- [ ] 🟥 **Step 3: Replace stub with real Cactus inference** — *Critical: API integration*

  **Context:** function_gemma.py currently uses `_stub_on_device_response` when `_CACTUS_AVAILABLE` is False. When Cactus imports, we must call real inference and parse output.

  **Subtasks (all required):**
  - [ ] 🟥 **Prompt builder:** Copy `_build_prompt` from v2 and replace alarm/timer hints with welding hints (voltage, angle, current, session ID). 270M is prompt-sensitive; without message-specific hints it may call the wrong tool or omit args. This work is not optional.
  - [ ] 🟥 **Tools format:** Wrap WARP_TOOLS as `[{"type":"function","function":t} for t in tools]` before passing to cactus_complete. Raw WARP_TOOLS = malformed; model returns non-tool output.
  - [ ] 🟥 **Output parsing:** cactus_complete returns raw text, not JSON. Copy `_try_parse` from v2 (handles markdown fences `\`\`\`json`, malformed quotes, etc.). Do not use `json.loads(raw)` — fails on `\`\`\`json\n{...}` and falls through to stub silently.
  - [ ] 🟥 **<50% spike:** If spike decision is <50%, skip on-device path entirely; call `_generate_cloud` directly for all queries.

  **Code snippet (integrate into existing function_gemma.py):**

  ```python
  # After successful cactus import. Use actual names from Step 1 grep.
  from cactus import cactus_init, cactus_complete  # ← replace with grep results

  _MODEL = None  # Thread-safe singleton

  def _ensure_cactus_warm():
      global _MODEL, _cactus_initialized
      if not _CACTUS_AVAILABLE or _MODEL is not None:
          return
      with _cactus_lock:
          if _MODEL is not None:
              return
          _MODEL = cactus_init(_WEIGHTS_PATH)
          wrapped = [{"type":"function","function":t} for t in WARP_TOOLS]
          cactus_complete(_MODEL, [{"role":"user","content":"test"}], tools=wrapped, force_tools=True, max_tokens=8)
          _cactus_initialized = True

  # In generate_hybrid, on-device branch:
  # If spike <50%: skip this block; call _generate_cloud directly for all queries.
  if _CACTUS_AVAILABLE and _MODEL is not None:
      wrapped_tools = [{"type":"function","function":t} for t in tools]
      prompt = _build_prompt(messages, last_msg)  # welding hints from v2
      raw = cactus_complete(_MODEL, prompt, tools=wrapped_tools, force_tools=True, max_tokens=128)
      parsed = _try_parse(raw)  # v2: handles ```json, malformed quotes — NOT json.loads(raw)
      calls = parsed.get("function_calls", []) if isinstance(parsed, dict) else []
      recovered = _recover_arguments(calls, tools, last_msg)  # pass calls list, not parsed
      result = {"function_calls": recovered, "source": "on-device"}
  else:
      result = _stub_on_device_response(last_msg)
  ```

  **What it does:** Builds prompt with welding hints; wraps tools; calls cactus_complete; parses via _try_parse; recovers args on the **calls list**; validates; returns or escalates.

  **Why this approach:** json.loads(raw) fails on markdown-wrapped output; wrong arg to _recover_arguments = recovery does nothing. _build_prompt steers 270M to correct tool.

  **Assumptions:** API names from Step 1 grep. v2 has _try_parse and _build_prompt to copy.

  **Risks:** API mismatch; missing _try_parse = parse errors. Mitigation: grep first; copy v2 parsing logic.

  **✓ Verification Test:**

  **Action:** With Cactus in place, run `python backend/weld_demo.py`; Scenario 1 and 2 should show source=on-device with real tool calls

  **Expected Result:** SOURCE: on-device; TOOL: check_parameter_threshold; ARGS with voltage/angle

  **Pass Criteria:** Real inference; no stub for measurement queries; validation still rejects wire_feed

---

- [ ] 🟥 **Step 4: Welding argument recovery and validation** — *Critical: data flow*

  **Context:** 270M may omit or malform args. Recovery extracts value, min, max, session_id from message text.

  **Pre-step (do before writing recovery):** Verify warp_tools field names. Run:
  ```bash
  python -c "from warp_tools import WARP_TOOLS; print(list(WARP_TOOLS[0]['parameters']['properties'].keys()))"
  ```
  If output includes `min_value`/`max_value` instead of `min`/`max`, use those keys in recovery. Wrong keys = validation fails silently.

  **_MEASUREMENT_PATTERN:** Defined in function_gemma.py as `re.compile(r'\d+\.?\d*\s*(?:V|A|°|degrees|volts|amps)', re.IGNORECASE)`. Used for value extraction. If working in fresh context, ensure this exists before calling _recover_arguments.

  **Code snippet (_recover_arguments):**

  ```python
  import re

  # Field names from warp_tools — verify with pre-step above
  _RANGE_MIN_KEY = "min"   # or "min_value" if warp_tools uses that
  _RANGE_MAX_KEY = "max"   # or "max_value" if warp_tools uses that

  # _MEASUREMENT_PATTERN: re.compile(r'\d+\.?\d*\s*(?:V|A|°|degrees|volts|amps)', re.IGNORECASE)

  # Two patterns — never [-–to]+ (character class bug)
  _RANGE_HYPHEN = re.compile(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)')
  _RANGE_TO = re.compile(r'(\d+\.?\d*)\s+to\s+(\d+\.?\d*)')

  def _recover_arguments(calls, tools, msg):
      for c in calls:
          args = c.setdefault("arguments", {})
          # value from measurement (e.g. 28V, 52 degrees)
          m = _MEASUREMENT_PATTERN.search(msg)
          if m and args.get("value") is None:
              args["value"] = float(re.search(r'\d+\.?\d*', m.group()).group())
          # min, max from range (18-24, 18 to 24)
          for r in (_RANGE_HYPHEN.search(msg), _RANGE_TO.search(msg)):
              if r and (args.get(_RANGE_MIN_KEY) is None or args.get(_RANGE_MAX_KEY) is None):
                  args[_RANGE_MIN_KEY], args[_RANGE_MAX_KEY] = float(r.group(1)), float(r.group(2))
                  break
          # session_id: WS-NNN
          if args.get("session_id") is None:
              sid = re.search(r'WS-\d+', msg)
              if sid:
                  args["session_id"] = sid.group()
      return calls
  ```

  **What it does:** Fills missing value, min, max, session_id from regex on message.

  **Why this approach:** 270M is small; often omits args. Recovery keeps validation passing without changing model.

  **Assumptions:** Field names verified by pre-step. Current warp_tools uses `min`/`max` — confirm before coding.

  **Risks:** Wrong field names = silent failure. Mitigation: pre-step. Regex edge cases: unit test both patterns.

  **✓ Verification Test:**

  **Action:** Unit test _recover_arguments with "voltage 28V range 18-24", "18 to 24", "session WS-042"

  **Expected Result:** value=28, min=18, max=24; session_id=WS-042

  **Pass Criteria:** All 3 demo queries produce correct tool calls; regex handles "18 to 24", "18-24", "18–24"

---

- [ ] 🟥 **Step 5: Verification and demo**

  **Subtasks:**
  - [ ] 🟥 Run all 5 scenarios: sources correct (on-device, cloud, on-device→cloud, offline)
  - [ ] 🟥 `python backend/weld_demo.py --offline` — zero network
  - [ ] 🟥 Two concurrent POSTs — both return 200
  - [ ] 🟥 `python backend/check_env.py` — all pass

  **✓ Verification Test:**

  **Action:** Full E2E: weld_demo (5 scenarios), weld_demo --offline, check_env

  **Expected Result:** No blank text; escalation visible for Scenario 5; offline shows canned message

  **Pass Criteria:** All 5 scenarios; offline; concurrent; check_env green

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 0** | Cactus imports | Run the import test from Step 1 verification (function name from grep) | ⬜ |
| | Spike complete | spike_test.py run; rate documented | ⬜ |
| **Phase 1** | Real inference | Scenario 1 → on-device with real tool call | ⬜ |
| | Argument recovery | Unit test _recover_arguments | ⬜ |
| | check_env | `python backend/check_env.py` | ⬜ |

---

## Risk Heatmap

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| **Step 1** | 🔴 **70%** | Cactus binaries wrong Mac/ABI; dylib errors | Import test on demo machine before coding |
| **Step 2** | 🟡 **50%** | 270M cannot produce valid tool calls | Spike on day 1; decision table |
| **Step 4** | 🟡 **30%** | Range regex character class bug | Unit test "18 to 24", "18-24", "18–24" |

---

## Success Criteria

| Feature | Target Behavior | Verification |
|---------|----------------|---------------|
| Cactus import | Import succeeds (Step 1 verification) | Import test from Step 1 |
| Real inference | Scenario 1, 2 → source=on-device, real tool calls | weld_demo |
| Argument recovery | value, min, max, session_id from message | Unit test |
| Escalation | Scenario 5 → on-device→cloud | weld_demo |
| Offline | --offline → canned response, zero network | weld_demo --offline |
| check_env | All checks pass | python backend/check_env.py |

---

## Spike Test Script (Reference)

**Critical:** cactus_complete expects tools in `[{"type":"function","function":t}]` format, not raw WARP_TOOLS. Passing WARP_TOOLS directly yields malformed tools — model may return non-tool output and spike shows 0/10 valid when the issue is tool format, not model capability.

```python
# backend/spike_test.py
import sys
import re
import json
sys.path.insert(0, 'cactus/python/src')
from cactus import cactus_init, cactus_complete
from warp_tools import WARP_TOOLS

def _try_parse(raw):
    """Minimal v2-style parse: strip ```json fences, handle malformed output."""
    s = raw.strip()
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', s)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}
wrapped_tools = [{"type": "function", "function": t} for t in WARP_TOOLS]
model = cactus_init('cactus/weights/functiongemma-270m-it')
query = "voltage is 28V, acceptable range 18-24V"
for i in range(10):
    raw = cactus_complete(model, [{"role":"user","content":query}], tools=wrapped_tools, force_tools=True, max_tokens=128)
    parsed = _try_parse(raw)
    calls = parsed.get("function_calls", []) if isinstance(parsed, dict) else []
    valid = any(c.get("name")=="check_parameter_threshold" and c.get("arguments",{}).get("parameter")=="voltage" for c in calls)
    print(f"Run {i+1}: {'OK' if valid else 'FAIL'} {raw[:80]}...")
```

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes.**
