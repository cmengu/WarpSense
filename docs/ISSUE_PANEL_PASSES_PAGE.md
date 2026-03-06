# Issue: Panel Passes Page — Data Loading + Layout Shell

**Type:** Feature  
**Priority:** Normal  
**Effort:** ~45 min  
**Labels:** `frontend` `panel` `replay` `data-loading`

---

## TL;DR

Create a new Next.js App Router page at `/panel/[panelId]/passes` that loads all weld-pass sessions for a panel and renders a layout shell (3D placeholder + defect panel placeholder). Do not modify the existing replay page. Uses `Promise.allSettled` for resilient parallel fetch; 404s on individual sessions must not crash the page.

---

## Current State vs Expected Outcome

### Current State
- No panel-centric route exists
- Dashboard links "View weld passes" to `/replay/[sessionId]` (single latest session only)
- `PANELS` is hardcoded in `dashboard/page.tsx` and not shared

### Expected Outcome
- New route: `/panel/[panelId]/passes` (e.g. `/panel/PANEL-2B/passes`)
- Loads all sessions for a panel: `sess_PANEL-2B_001` through `sess_PANEL-2B_005`
- Layout: top bar (panel label, session count, back to Dashboard), 70% canvas placeholder, 30% defect panel placeholder
- Graceful handling: individual 404s logged and skipped; `alertOnReplayFailure` only if ALL sessions fail

---

## Implementation Requirements

### 1. Extract PANELS to Shared Module

**Do not duplicate PANELS.** Extract from dashboard and import in both places.

- **Create** `my-app/src/data/panels.ts` — export `PANELS`, `getSessionIdForPanel`, and `getSessionIdsForPanel`
- **Update** `my-app/src/app/(app)/dashboard/page.tsx` — import `PANELS` and `getSessionIdForPanel` from `@/data/panels`; remove local definitions

**Critical:** `getSessionIdForPanel` (singular) must be preserved unchanged — dashboard uses it for the "View weld passes" link to the *latest* pass. Co-export both helpers.

```typescript
/** Latest pass only — used by dashboard "View weld passes" link. */
export function getSessionIdForPanel(panel: Panel): string {
  return `sess_${panel.id}_${String(panel.sessionCount).padStart(3, "0")}`;
}

/**
 * All pass session IDs _001 through _00N.
 * Assumption: sessions are numbered sequentially with no gaps (no deleted/skipped passes).
 * 404s on individual IDs are handled gracefully by the caller.
 */
export function getSessionIdsForPanel(panel: Panel): string[] {
  return Array.from({ length: panel.sessionCount }, (_, i) =>
    `sess_${panel.id}_${String(i + 1).padStart(3, "0")}`
  );
}
```

### 2. Data Loading

- **Params pattern:** Copy verbatim from `my-app/src/app/replay/[sessionId]/page.tsx` — `params: Promise<{ panelId: string }>`, outer page wraps in `<Suspense>`, inner component calls `const { panelId } = use(params)` inside Suspense. Next.js 15/16 requires `use(params)` for async params.
- Find panel: `PANELS.find(p => p.id === panelId)` — 404-style error if not found
- Generate session IDs: `getSessionIdsForPanel(panel)` → `sess_${panelId}_001` … `sess_${panelId}_00N`
- Fetch: `Promise.allSettled(sessionIds.map(id => fetchSession(id, { limit: 2000, include_thermal: true })))`
- **Critical:** `allSettled` never throws — it always resolves. There is no `err` in scope. Extract errors from results.
- On **rejected**: `logWarn("panel_passes", \`Session ${sessionId} failed\`, { panelId, sessionId, error: String(err) })`, skip that session
- On **fulfilled**: keep the Session (fetchSession throws on 404, never returns null)
- **All sessions fail:** Extract first error from rejected results and pass to alertOnReplayFailure. Use this exact shape:

```typescript
const results = await Promise.allSettled(...)
const failures = results.filter(r => r.status === "rejected")
const sessions = results
  .filter((r): r is PromiseFulfilledResult<Session> => r.status === "fulfilled")
  .map(r => r.value)

if (sessions.length === 0) {
  const firstError = failures.length > 0
    ? (failures[0] as PromiseRejectedResult).reason
    : new Error("No sessions to load")
  alertOnReplayFailure(
    `panel_passes_${panelId}`,
    firstError,
    { source: "panel_passes", panelId }
  )
  setError("No sessions could be loaded")
  return
}
```

- State: `sessions: Session[]`, `loading`, `error`

### 3. Layout (Placeholders Only)

- **Dark theme:** Copy from replay page: `min-h-screen bg-zinc-50 dark:bg-black`
- **Layout:** CSS `grid grid-cols-[70%_30%]` — explicit 70/30 split
- **Top bar:** Panel label (e.g. "PANEL-2B — Tank Top — Centre" from `panel.label`), session count, back arrow → `href="/dashboard"` (route group `(app)` does not appear in URL)
- **Left (70%):** Dark canvas placeholder — "3D Panel View — [N] weld passes loaded"
- **Right (30%):** Placeholder — "Defect Detail Panel"
- **Loading:** Spinner in canvas area
- **All failed:** Error state with panel ID + "Check that session data is seeded for this panel"

### 4. Constraints

- **Do NOT touch** `my-app/src/app/replay/[sessionId]/page.tsx`
- Use `fetchSession` from `@/lib/api` (same as replay)
- Use `alertOnReplayFailure`, `logWarn` from `@/lib/logger`
- Use `useEffect` with `cancelled`/`mounted` flag for cleanup

---

## Files to Create/Edit

| File | Change |
|------|--------|
| `my-app/src/data/panels.ts` | **Create** — export `PANELS`, `getSessionIdForPanel`, `getSessionIdsForPanel` |
| `my-app/src/app/(app)/dashboard/page.tsx` | Import `PANELS`, `getSessionIdForPanel` from `@/data/panels`; remove local definitions |
| `my-app/src/app/panel/[panelId]/passes/page.tsx` | **Create** — page with data loading + layout shell |

---

## Out of Scope (This Issue)

- 3D panel viewer implementation
- Defect detail panel implementation
- Any changes to replay page

---

## Risk / Notes

- `panel.sessionCount` is hardcoded in PANELS; may not match actual DB. Handle 404s gracefully.
- Dashboard uses `getSessionIdForPanel` for *latest* pass only (`sess_PANEL-X_005`). This page fetches *all* passes 001–00N. Keep helper semantics clear.

---

## Decisions Log (Logic Check — Carry Into Implementation)

| Decision | Value |
|----------|-------|
| `alertOnReplayFailure` first arg | `panel_passes_${panelId}` (session-like ID), plus `{ source: "panel_passes", panelId }` in additionalInfo |
| `logWarn` on per-session rejection | `logWarn("panel_passes", \`Session ${sessionId} failed\`, { panelId, sessionId, error: String(err) })` |
| Dashboard helper preservation | Both `getSessionIdForPanel` (singular) and `getSessionIdsForPanel` (plural) co-exported from `@/data/panels.ts` |
| Session ID assumption | Sessions numbered _001–_00N with no gaps; document in helper comment |
| Params pattern | `use(params)` inside Suspense — copy verbatim from replay page |
| Layout | `grid grid-cols-[70%_30%]`; dark theme `min-h-screen bg-zinc-50 dark:bg-black`; back → `/dashboard` |
| All-sessions-fail `err` | `allSettled` never throws; extract `firstError` from `(failures[0] as PromiseRejectedResult).reason` before calling `alertOnReplayFailure` |

---

## Verification (Before Finishing)

- [ ] Route `/panel/PANEL-2B/passes` resolves without 404 (navigate or direct URL)
- [ ] Dashboard still renders after import refactor; "View weld passes" links work

---

## Resolution Bridge (Implementation Reference)

### Decisions Log — Issue → Resolution

| Issue | Resolution | Source | Affects |
|-------|------------|--------|---------|
| `alertOnReplayFailure` received raw panelId; signature expects session-like string | First arg: `panel_passes_${panelId}`; additionalInfo: `{ source: "panel_passes", panelId }` | `my-app/src/lib/logger.ts` | Step 3 (all-fail branch) |
| `Promise.allSettled` never throws — `err` not in scope | Extract `firstError` from `(failures[0] as PromiseRejectedResult).reason` before calling `alertOnReplayFailure` | Logic Check | Step 3 (all-fail branch) |
| `logWarn` takes `(context, message, additionalInfo?)` — two required strings | `logWarn("panel_passes", \`Session ${sessionId} failed\`, { panelId, sessionId, error: String(err) })` | `my-app/src/lib/logger.ts` | Step 3 (per-session rejection) |
| `getSessionIdForPanel` (singular) used by dashboard would be lost | Both `getSessionIdForPanel` and `getSessionIdsForPanel` co-exported from `@/data/panels.ts` | Human decision | Step 1, Step 2 |
| `use(params)` vs `await params` — Next.js 15/16 requires `use(params)` inside Suspense | Outer page with `<Suspense>`; inner component `const { panelId } = use(params)` — copy from replay page | Replay page | Step 3 (params) |
| Back arrow URL unclear — route group `(app)` does not appear in URL | `href="/dashboard"` | App Router convention | Step 4 (Layout) |
| Layout split ambiguous — flex vs grid | `grid grid-cols-[70%_30%]` | Human decision | Step 4 (Layout) |
| `fetchSession` on 404 | Throws — never returns null; filter on `status === "fulfilled"` only | `my-app/src/lib/api.ts` | Step 3 |

### Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| `alertOnReplayFailure` first arg type | Session-like string, not raw panelId | logger.ts | Yes | ✓ `panel_passes_${panelId}` |
| `err` scope in all-fail branch | `allSettled` never throws — extract from results array | Logic Check | Yes | ✓ `(failures[0] as PromiseRejectedResult).reason` |
| `logWarn` argument shape | Two required strings + optional object | logger.ts | Yes | ✓ Specified exactly |
| Singular helper preservation | Dashboard breaks if `getSessionIdForPanel` removed | dashboard/page.tsx | Yes | ✓ Both helpers co-exported |
| Params pattern | `use(params)` inside Suspense for Next.js 15/16 | Replay page | Yes | ✓ Copy verbatim |
| Back arrow href | Route group `(app)` invisible in URL | App Router | Yes | ✓ `/dashboard` |
| Layout implementation | Grid vs flex ambiguity | Human decision | Yes | ✓ `grid grid-cols-[70%_30%]` |
| `fetchSession` on 404 | Throws — never returns null | api.ts | Yes | ✓ Filter on `status === "fulfilled"` only |

No unresolved flaws. All decisions have exactly one answer.

### Steps Analysis

| Step | Criticality | Human Gate | Notes |
|------|-------------|------------|-------|
| **1 — Extract PANELS** | Critical | Yes — verify dashboard compiles; "View weld passes" links resolve before Step 2 | Pure data extraction; idempotent |
| **2 — Update dashboard import** | Critical | Yes — navigate to `/dashboard`; confirm 6 panel cards render; "View weld passes" links point to correct session IDs before Step 3 | Only source changes; idempotent |
| **3 — Data loading** | Critical | Yes — open network tab; navigate to `/panel/PANEL-2B/passes`; confirm 5 session fetches fire; canvas placeholder shows "5 weld passes loaded" | Core logic; all-fail branch has resolved flaws; idempotent |
| **4 — Layout shell** | Non-critical | No — visual check sufficient | Pure JSX; idempotent |

**Step 3 function signatures:**

- `fetchSession(sessionId, params?)` — throws on 404
- `logWarn("panel_passes", \`Session ${sessionId} failed\`, { panelId, sessionId, error: String(err) })`
- `alertOnReplayFailure(\`panel_passes_${panelId}\`, firstError, { source: "panel_passes", panelId })`
- `getSessionIdsForPanel(panel)` → `string[]`

---

## Vision Alignment

From `vision.md`: *"Something they can forward"* — Panel-centric view with all weld passes in one place supports surveyor reports and inspection workflows. Data loading shell unblocks 3D and defect panel work.
