# Panel Passes Page — Implementation Plan

**Source:** `docs/ISSUE_PANEL_PASSES_PAGE.md`  
**Overall Progress:** 0%  
**Estimated Effort:** ~45 min

---

## TL;DR

Create `/panel/[panelId]/passes` route that loads all weld-pass sessions for a panel and renders a layout shell (70/30 grid: canvas placeholder + defect panel placeholder). Extract `PANELS` to `@/data/panels.ts`; update dashboard import; create new page with `Promise.allSettled` data loading. Do not modify the replay page.

---

## Critical Decisions

| Decision | Choice |
|----------|--------|
| **1** | `alertOnReplayFailure` first arg: `panel_passes_${panelId}` (session-like ID); additionalInfo: `{ source: "panel_passes", panelId }` |
| **2** | `allSettled` never throws — capture `firstError` in the single `results.forEach` loop (first rejected result); use for `alertOnReplayFailure` when `sessions.length === 0` |
| **3** | `logWarn("panel_passes", \`Session ${sessionId} failed\`, { panelId, sessionId, error: String(err) })` on per-session rejection |
| **4** | Both `getSessionIdForPanel` (singular) and `getSessionIdsForPanel` (plural) co-exported from `@/data/panels.ts`; dashboard imports both |
| **5** | Sessions numbered _001–_00N with no gaps; document assumption in helper comment |
| **6** | Params: `use(params)` inside Suspense — copy verbatim from `my-app/src/app/replay/[sessionId]/page.tsx` |
| **7** | Layout: `grid grid-cols-[70%_30%]`; dark theme `min-h-screen bg-zinc-50 dark:bg-black`; back → `href="/dashboard"` |

---

## Pre-Flight — Run Before Any Code Changes

```bash
# 1. Confirm PANELS exists in dashboard
grep -n "const PANELS" my-app/src/app/\(app\)/dashboard/page.tsx
# Expected: 1 match

# 2. Confirm getSessionIdForPanel exists
grep -n "getSessionIdForPanel" my-app/src/app/\(app\)/dashboard/page.tsx
# Expected: 2+ matches (definition + usage)

# 3. Confirm replay page uses use(params) pattern (single quotes avoid bash subshell)
grep -n 'use(params)' my-app/src/app/replay/\[sessionId\]/page.tsx
# Expected: 1 match

# 4. Confirm data/panels.ts does NOT exist
ls my-app/src/data/panels.ts 2>/dev/null || echo "File does not exist"
# Expected: File does not exist

# 5. Confirm panel passes route does NOT exist
ls my-app/src/app/panel/\[panelId\]/passes/page.tsx 2>/dev/null || echo "Route does not exist"
# Expected: Route does not exist

# 6. Baseline TypeScript check
cd my-app && npx tsc --noEmit
# Expected: exit 0
```

**Baseline Snapshot:**
```
PANELS in dashboard        : ____
getSessionIdForPanel usage : ____
use(params) in replay      : ____
data/panels.ts exists      : no (must be no)
panel passes route exists  : no (must be no)
TSC exit code             : ____
```

---

## Tasks

### Step 1 — Extract PANELS to Shared Module

**Criticality:** Critical (dashboard breaks if done wrong)  
**Human Gate:** Yes — verify dashboard compiles; "View weld passes" links resolve before Step 2

**Create** `my-app/src/data/panels.ts`:

1. Import `Panel` from `@/types/panel` — also verify and import any enums/types referenced inside the PANELS array (e.g. `ConstructionStage`, `InspectionDecision` from `@/types/panel`)
2. Copy `PANELS` array from dashboard (the `const PANELS: Panel[] = [...]` declaration)
3. Export `getSessionIdForPanel(panel: Panel): string` — unchanged from dashboard
4. Export `getSessionIdsForPanel(panel: Panel): string[]` — new helper per issue spec
5. Add JSDoc: "Assumption: sessions numbered _001–_00N with no gaps"

**Verification:**
```bash
cd my-app && npx tsc --noEmit
# Expected: exit 0 (panels.ts compiles in isolation)
```

**Deliverable:** `my-app/src/data/panels.ts` exists; exports `PANELS`, `getSessionIdForPanel`, `getSessionIdsForPanel`

---

### Step 2 — Update Dashboard Import

**Criticality:** Critical (dashboard is live)  
**Human Gate:** Yes — navigate to `/dashboard`; confirm 6 panel cards render; "View weld passes" links point to correct session IDs before Step 3

**Edit** `my-app/src/app/(app)/dashboard/page.tsx`:

1. Add: `import { PANELS, getSessionIdForPanel } from "@/data/panels"`
2. Remove: the `const PANELS = [...]` array declaration (delete by content pattern, not line number — line numbers may have shifted)
3. Remove: the `getSessionIdForPanel` function definition (delete by content pattern)
4. Keep: `PANEL_MOCK_SCORES`, `getRiskLevel`, and all other logic unchanged

**Verification:**
```bash
cd my-app && npx tsc --noEmit
# Expected: exit 0
```

**Manual check:** Navigate to `/dashboard`; all 6 panel cards render; "View weld passes" links resolve to `/replay/sess_PANEL-X_005` (latest pass per panel)

---

### Step 3 — Create Panel Passes Page (Data Loading + Layout)

**Criticality:** Critical (core logic)  
**Human Gate:** Yes — network tab: 5 fetches fire; canvas shows "5 weld passes loaded"

**Create** `my-app/src/app/panel/[panelId]/passes/page.tsx`:

**Three-component structure (required — do not collapse):**
- **PanelPassesPage** = default export; contains the `<Suspense>` boundary only; passes `params` to child
- **PanelPassesPageWithParams** = child of Suspense; calls `const { panelId } = use(params)`; passes `panelId` down
- **PanelPassesPageInner** = receives `panelId: string`; owns all state (sessions, loading, error) and layout

Follow the same structural pattern as lines 96–130 of the replay page — use the same shape with component names PanelPassesPage, PanelPassesPageWithParams, PanelPassesPageInner. Do not copy literally; the replay uses ReplayPage, ReplayPageWithAsyncParams, ReplayPageInner.

**State (in PanelPassesPageInner):** `const [panel, setPanel] = useState<Panel | null>(null)` — panel is set when found so the top bar can render safely during loading/error. Top bar uses `panel?.id ?? panelId` and `panel?.label ?? "…"` to avoid crashes before panel is resolved.

**Data loading (useEffect with mounted/cancelled flag, in PanelPassesPageInner):**
1. Find panel: `const found = PANELS.find(p => p.id === panelId)` → if not found, set error and return. If found: `setPanel(found)` immediately.
2. Session IDs: `getSessionIdsForPanel(found)` (use `found`, not `panel` — panel state may not have updated yet in same tick)
3. Fetch: `Promise.allSettled(sessionIds.map(id => fetchSession(id, { limit: 2000, include_thermal: true })))`
4. Process results — **single `results.forEach` loop**; no separate `failures` variable (avoids redundancy and type casts):

```typescript
const sessions: Session[] = []
let firstError: unknown = null

results.forEach((result, i) => {
  if (result.status === "fulfilled") {
    sessions.push(result.value)
  } else {
    if (!firstError) firstError = result.reason
    logWarn("panel_passes", `Session ${sessionIds[i]} failed`, {
      panelId, sessionId: sessionIds[i], error: String(result.reason)
    })
  }
})

if (sessions.length === 0) {
  alertOnReplayFailure(
    `panel_passes_${panelId}`,
    firstError ?? new Error("No sessions to load"),
    { source: "panel_passes", panelId }
  )
  setError("No sessions could be loaded")
  return
}
```

5. State: `setSessions(sessions)`, `setLoading(false)`

**Layout:**
- Container: `min-h-screen bg-zinc-50 dark:bg-black`
- Grid: `grid grid-cols-[70%_30%]`
- Top bar: `${panel?.id ?? panelId} — ${panel?.label ?? "…"}` (em dash; safe during loading when panel is null), session count, back arrow `Link href="/dashboard"`
- Left: "3D Panel View — [N] weld passes loaded" (dark placeholder)
- Right: "Defect Detail Panel" (placeholder)
- Loading: use whatever loading indicator pattern exists in the replay page or dashboard; do not introduce new UI dependencies
- Error: "Check that session data is seeded for this panel"

**Verification:**
```bash
cd my-app && npx tsc --noEmit
# Expected: exit 0
```

**Manual check:** Navigate to `/panel/PANEL-2B/passes`; network tab shows 5 session fetches; canvas shows "5 weld passes loaded"

---

### Step 4 — Verification (Final)

**Checklist:**
- [ ] Route `/panel/PANEL-2B/passes` resolves without 404
- [ ] Dashboard still renders; "View weld passes" links work
- [ ] No lint errors
- [ ] No console errors on page load

---

## Files Summary

| File | Action |
|------|--------|
| `my-app/src/data/panels.ts` | **Create** |
| `my-app/src/app/(app)/dashboard/page.tsx` | **Edit** — import from panels |
| `my-app/src/app/panel/[panelId]/passes/page.tsx` | **Create** |

---

## Out of Scope

- 3D panel viewer
- Defect detail panel
- Changes to replay page

---

## Reference

- **Issue:** `docs/ISSUE_PANEL_PASSES_PAGE.md`
- **Replay page pattern:** `my-app/src/app/replay/[sessionId]/page.tsx` (lines 96–130)
- **Logger:** `my-app/src/lib/logger.ts` — `alertOnReplayFailure`, `logWarn`
- **API:** `my-app/src/lib/api.ts` — `fetchSession` (throws on 404)
