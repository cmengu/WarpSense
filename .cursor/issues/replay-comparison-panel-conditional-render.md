# Replay page: Right-side 3D heatmap panel missing when comparison session fails

## TL;DR

On the **replay page** (not compare page), the right-side 3D heatmap container (`TorchWithHeatmap3D` with blue border) only renders when `showComparison && comparisonSession?.frames` is true. When the comparison session fails to load or has no frames, we show a different placeholder — so the expected heatmap div is "missing" in DevTools.

---

## Current state

- **Compare page** (`/compare/sess_A/sess_B`): Works. Both sessions fetched by ID from URL. All three 2D heatmaps (Session A, Delta, Session B) always render.
- **Replay page** (`/replay/sess_A`): Right panel uses a **fixed** comparison session from `NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID` (default: `sess_novice_001`). No way to pick comparison session from the page.

### Conditional logic (replay page, lines 790–843)

| Condition | Result |
|-----------|--------|
| `showComparison && comparisonSession?.frames` | TorchWithHeatmap3D (blue-bordered heatmap div) |
| `showComparison && !(comparisonSession?.frames)` | "Comparison session not available" placeholder (different div) |
| `!showComparison` | Nothing (`null`) |

When the comparison fetch returns 404 or fails, `comparisonSession` is set to `null` → we show the placeholder, so the heatmap container div is not in the DOM.

---

## Expected vs actual

| Scenario | Expected | Actual |
|----------|----------|--------|
| Compare expert vs novice aluminum on replay | Right 3D panel shows novice session | Right panel shows "Comparison session not available" unless env points to that session |
| User wants to compare current session with a specific other | Can pick comparison session | Must set env var; no UI/URL to choose |
| DevTools: locate heatmap container | Find blue-bordered div | Div not present when comparison session unavailable |

---

## Relevant files

| File | Touching |
|------|----------|
| `my-app/src/app/replay/[sessionId]/page.tsx` | `showComparison`, `comparisonSession`, right-panel conditional (790–843); comparison fetch (365–399); `getComparisonSessionId()` (73–87) |

---

## Root causes

1. **Fixed comparison session** — `COMPARISON_SESSION_ID` comes from env. To compare expert aluminium vs novice aluminium, you must set `NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID=sess_novice_aluminium_001_001`. Default `sess_novice_001` is mild steel, not aluminium.
2. **404 / fetch failure** — Comparison fetch fails → `setComparisonSession(null)` → placeholder instead of heatmap.
3. **Empty frames** — `comparisonSession?.frames` is falsy when frames array is empty → same placeholder.

---

## Proposed improvements

### Option A (low effort): Clarify "missing" state

- When comparison session is unavailable, show a clearer message: e.g. "Comparison session not available. Set `NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID` or use Compare page for custom pairs."
- Keeps current behavior; improves clarity.

### Option B (medium effort): URL param for comparison session

- Support `?compare=sess_novice_aluminium_001_001` on replay page.
- When present, use that session as comparison instead of env.
- Enables expert vs novice aluminium without env changes.

### Option C (larger): Compare session selector UI

- Dropdown or modal on replay page to pick from known sessions.
- Requires session list API or predefined list.

---

## Risk / notes

- **WebGL limit**: Max 2 TorchWithHeatmap3D per page (see `constants/webgl.ts`). Replay already uses 2 (left + right). Do not add more.
- **Compare page vs replay**: Compare page uses 2D `HeatMap`; replay uses 3D `TorchWithHeatmap3D`. Different components, different DOM structure.

---

## Type / priority / effort

| Label | Value |
|-------|-------|
| Type | Bug (missing expected UI) / Improvement (flexibility) |
| Priority | Normal |
| Effort | Low–Medium (Option A); Medium (Option B) |

---

## Product vision

Replay comparison should make it easy to compare current session with a chosen baseline (e.g. expert aluminium vs novice aluminium). The current env-only setup limits this and can make the right panel appear "missing" when the default comparison session doesn’t exist or doesn’t match the weld type.
