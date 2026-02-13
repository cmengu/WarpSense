# Code Review Report

**Date:** 2026-02-13  
**Scope:** Entire codebase (frontend, backend, tests)  
**Focus:** Critical areas of failure first  
**Status:** Current state post-fixes

---

## ✅ Looks Good

- **SQL injection:** All backend queries use SQLAlchemy ORM with bound parameters — no raw SQL concatenation
- **XSS:** No `dangerouslySetInnerHTML`, `eval`, or `innerHTML` assignments
- **Secrets:** No hardcoded passwords, API keys, or tokens in code
- **WebGL context loss:** TorchViz3D has `webglcontextlost` / `webglcontextrestored` handlers and user-facing overlay
- **ErrorBoundary:** Used around HeatMap, TorchAngleGraph, ScorePanel, TorchViz3D; uses `logError` for reporting
- **Centralized logger:** `logError`, `logWarn`, `alertOnReplayFailure` in `lib/logger.ts`; replay failures trigger webhook when configured
- **Dashboard links:** Correctly point to `sess_expert_001` and `sess_novice_001` with proper seed instructions
- **Error handling:** `err instanceof Error ? err.message : String(err)` used consistently; cancelled/mounted flags on async effects
- **Backend validation:** Frame model has Pydantic validators (volts/amps non-negative, angle 0–360, thermal snapshot constraints)
- **Async cleanup:** Replay, compare, ScorePanel, seagull, page use cancelled/mounted flags to avoid setState after unmount
- **Data integrity:** Append-only sensor data, deterministic feature extraction, stateless scoring
- **Dev routes:** Seed/wipe protected by ENV/DEBUG check; return 403 when not in dev mode
- **Exception sanitization:** `add_frames` returns generic "Internal error" for unexpected exceptions
- **iPad placeholders:** Typed placeholders return safe empty data; no thrown errors
- **Performance:** useMemo used for expensive HeatMap/useFrameData/useSessionComparison/useSessionMetadata computations

---

## ⚠️ Issues Found

### LOW

- **[LOW]** [ipad_app/api/backendClient.ts:61] — Direct `console.debug` in placeholder
  - **Issue:** Uses `console.debug` with eslint-disable instead of centralized logger.
  - **Fix:** Acceptable for placeholder; switch to logger when wiring real implementation.

- **[LOW]** [ipad_app/api/backendClient.ts:12] — Unused `API_URL` variable
  - **Issue:** Declared but never used until implementation.
  - **Fix:** Add `// Reserved for implementation` comment or remove; lint may flag.

- **[LOW]** [my-app/src/app/seagull/page.tsx:54-56] — Rejected fetches not logged
  - **Issue:** When `fetchScore` fails for a welder, error is stored in `WelderScoreResult` but never logged. "Score unavailable" shows in UI but no trace for debugging.
  - **Fix:** Add `logWarn("SeagullDashboard", "Score unavailable", { welder: w.id, error: r.reason })` when `r.status === "rejected"`.

- **[LOW]** [ai_models/similarity_model.py:10] — TODO placeholder
  - **Issue:** `TODO: Implement similarity model when Phase 2 begins`.
  - **Fix:** Acceptable for MVP; ensure not called by production code.

---

## 📊 Summary

| Metric | Count |
|--------|-------|
| Files reviewed | ~55+ |
| Critical issues | 0 |
| High severity | 0 |
| Medium severity | 0 |
| Low severity | 4 |

---

## Severity Levels

- **CRITICAL** — User-facing breakage, data loss, security
- **HIGH** — Bugs, poor UX, type-safety violations
- **MEDIUM** — Maintainability, error clarity
- **LOW** — Style, minor improvements

---

## Recommended Fix Order

1. **Dashboard session links** — Fix immediately; users hit 404.
2. **page.tsx error handling + cleanup** — Prevents blank errors and unmount warnings.
3. **Replay page `console.warn`** — Align with logging standards.
4. **ipad_app types** — Replace `any` if this module is in active use.
5. **Welder error message** — Improve debugging without exposing internals.
6. **Backend exception sanitization** — Reduce risk of leaking internal errors.
7. **Logger production behavior** — Match documented "silent" behavior.
