# Replay Comparison Panel — Exploration & Implementation Plan

## Summary of issue

On replay page (`/replay/[sessionId]`), the right-side 3D heatmap (`TorchWithHeatmap3D`) only renders when `showComparison && comparisonSession?.frames`. The comparison session ID comes from **env only** (`NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID`, default `sess_novice_001`). No way to pick a comparison session from the page or URL.

**Desired**: Compare current session with a chosen baseline (e.g. expert aluminium vs novice aluminium) without changing env.

---

## Codebase analysis

### Current data flow

```
User visits /replay/sess_expert_aluminium_001_001
    ↓
ReplayPageInner mounts
    ↓
useState: sessionData (null), comparisonSession (null), showComparison (true)
    ↓
useEffect #1: fetchSession(sessionId) → setSessionData
useEffect #2: if showComparison && COMPARISON_SESSION_ID
              fetchSession(COMPARISON_SESSION_ID) → setComparisonSession
              (COMPARISON_SESSION_ID = env or 'sess_novice_001')
    ↓
Right panel conditional:
  - showComparison && comparisonSession?.frames → TorchWithHeatmap3D ✓
  - showComparison && !(comparisonSession?.frames) → "Comparison session not available"
  - !showComparison → null
```

### Key integration points

| Location | Current behavior |
|----------|------------------|
| `getComparisonSessionId()` (lines 73–87) | Returns env or `'sess_novice_001'`; no URL input |
| `useSearchParams()` (line 139) | Used only for `?t=` deep-link; not for comparison |
| Comparison fetch `useEffect` (365–400) | Depends on `showComparison`, `COMPARISON_SESSION_ID`; no URL |
| Compare page link (579) | `href={/compare?sessionA=${sessionId}}` — pre-fills A only; user types B manually |

### Dependencies & constraints

- **WebGL limit**: Max 2 `TorchWithHeatmap3D` per page (`constants/webgl.ts`). Replay uses 2 (left + right). No extra canvases.
- **fetchSession**: Already used for both primary and comparison. Supports `limit`, `include_thermal`.
- **list sessions API**: `GET /api/sessions` returns 501 Not Implemented. No session list from backend.
- **Aggregate API**: `GET /api/sessions/aggregate?include_sessions=true` returns `sessions[]` with `session_id`. Used for supervisor export; could be repurposed for a dropdown, but adds dependency on that endpoint.

### Edge cases

1. **Invalid `?compare=`** — Session doesn’t exist (404). Same handling as env-based: `setComparisonSession(null)` → placeholder.
2. **Same session** — `?compare=sess_expert_aluminium_001_001` when current is that session. No special handling today; would render two identical 3D views.
3. **Empty frames** — `comparisonSession?.frames` is `[]`. Falsy → placeholder. Same as today.
4. **URL param vs env** — When both present, URL should override env for flexibility.

---

## High-level mock execution

### Option A: Clarify "missing" state (minimal)

**Data flow**: No new data; only copy change.

**Component structure**: Replay page placeholder div (around line 837) — change text.

```
Current: "Comparison session not available"
Proposed: "Comparison session not available. Set NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID or use Compare page for custom pairs."
```

**State / side effects**: None.

---

### Option B: URL param for comparison session (recommended)

**Data flow**:
```
User visits /replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001
    ↓
useSearchParams().get('compare') → compareParam = 'sess_novice_aluminium_001_001'
    ↓
effectiveComparisonId = compareParam ?? COMPARISON_SESSION_ID ?? undefined
    ↓
useEffect: if showComparison && effectiveComparisonId
           fetchSession(effectiveComparisonId) → setComparisonSession
    ↓
Right panel: same conditional; now uses comparison session from URL when present
```

**Component structure**: No new components. Replay page logic only.

**State**:
- `comparisonSession` (unchanged)
- Derived: `compareParam = searchParams.get('compare')`
- Derived: `effectiveComparisonId = compareParam ?? COMPARISON_SESSION_ID` (null/undefined → no fetch)

**Side effects**:
```ts
// useEffect deps: [showComparison, effectiveComparisonId]
// When effectiveComparisonId changes (URL or env), refetch comparison session
```

**Pseudocode**:
```ts
const compareParam = searchParams.get('compare');
const effectiveComparisonId = (compareParam?.trim() || undefined) ?? COMPARISON_SESSION_ID;

useEffect(() => {
  if (!showComparison || !effectiveComparisonId) {
    setComparisonSession(null);
    return;
  }
  let cancelled = false;
  fetchSession(effectiveComparisonId, { limit: 2000, include_thermal: true })
    .then((data) => { if (!cancelled) setComparisonSession(data); })
    .catch(() => { if (!cancelled) setComparisonSession(null); });
  return () => { cancelled = true; };
}, [showComparison, effectiveComparisonId]);
```

**Edge cases**:
- Loading: Same as today — left panel shows; right shows placeholder until fetch resolves.
- Error: `setComparisonSession(null)` → "Comparison session not available".
- `?compare=` (empty): Treat as "no compare param" → fall back to env.

---

### Option C: Compare session selector UI

**Data flow**:
```
User clicks dropdown → selects sess_novice_aluminium_001_001
    ↓
setComparisonSessionId(sess_novice_aluminium_001_001)
    ↓
useEffect: fetchSession(comparisonSessionId) → setComparisonSession
    ↓
(Optional) Update URL: router.replace(?compare=sess_novice_aluminium_001_001)
```

**Options for session list**:
1. **Hardcoded** — Known demo IDs from WELDER_ARCHETYPES (e.g. sess_expert_001, sess_novice_001, sess_expert_aluminium_001_001, sess_novice_aluminium_001_001). No API.
2. **Aggregate API** — `fetchAggregate({ include_sessions: true })` → `sessions[].session_id`. Adds API call and ties to supervisor data.
3. **New list endpoint** — Implement `GET /api/sessions`. Higher effort.

**Component structure**:
- New: `ComparisonSessionSelect` (or inline `<select>`) in replay metadata bar.
- Props: `value`, `onChange`, `options` (session IDs or `{id, label}`).

---

## Implementation approach

### Option B (URL param) — suggested

| File | Action | Reason |
|------|--------|--------|
| `my-app/src/app/replay/[sessionId]/page.tsx` | MODIFY | Add `compare` from `searchParams`, derive `effectiveComparisonId`, update useEffect deps and fetch logic |

**New files**: None.

**Rationale**:
- Small change: ~15 lines.
- No new components or APIs.
- Shareable links: `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001`.
- Backward compatible: no `?compare=` → same env-based behavior.

**Rejected**:
- New hook `useComparisonSession(compareParam)`: Overkill for one call site.
- Storing comparison ID in React state only: Loses URL shareability.

---

### Option A (message only)

| File | Action |
|------|--------|
| `my-app/src/app/replay/[sessionId]/page.tsx` | MODIFY — update placeholder text (line 838) |

~2 lines. Fastest win.

---

### Option C (dropdown)

| File | Action |
|------|--------|
| `my-app/src/app/replay/[sessionId]/page.tsx` | MODIFY — add state, dropdown, optional URL sync |
| `my-app/src/constants/demo-sessions.ts` (or similar) | NEW — hardcoded demo session IDs for dropdown |

More UX work; can be added later on top of Option B.

---

## Questions to clarify

1. **Scope**: Implement Option B (URL param) now, or Option A (message) only?
2. **URL sync for Option C**: If we add a dropdown later, should selecting a session also update `?compare=...` for shareable links?
3. **Same-session guard**: Block or warn when `?compare=` equals current `sessionId`?
4. **Compare page link**: Should the "Compare with another session" link on replay pre-fill both A and B when a comparison is active, e.g. `href={/compare?sessionA=${sessionId}&sessionB=${effectiveComparisonId}}`?
