# [Bug] WebGL context lost appears consistently throughout the project

## TL;DR

Users and developers see "THREE.WebGLRenderer: Context Lost" repeatedly across the app — on `/demo`, `/replay`, and `/dev/torch-viz` — leading to white/black screens, frozen 3D views, and noisy console output. Mitigations (context-loss handlers, 1–2 Canvas limit, documentation) exist but the problem persists. The core issue is that WebGL context loss is not fully prevented or surfaced in a predictable way across all pages. We need a project-wide strategy: centralize Canvas usage, ensure context-loss overlays are reliable, add loading fallbacks everywhere, and reduce or consolidate instances where possible. This aligns with our vision of a reliable, deterministic MVP for welding session visualization.

---

## Current State

**What exists:**

| File/Component | Current behavior | Limitations |
|----------------|------------------|--------------|
| `my-app/src/components/welding/TorchViz3D.tsx` | Renders one 3D Canvas; adds `webglcontextlost` / `webglcontextrestored` listeners in `onCreated`; shows overlay when `contextLost` is true | Overlay only appears after loss; no proactive prevention; each instance creates a new WebGL context |
| `documentation/WEBGL_CONTEXT_LOSS.md` | Documents error, causes, prevention checklist, fix examples | Not enforced in code; pages may violate guidelines |
| `LEARNING_LOG.md` | Records past incident (6 instances on /dev/torch-viz); DO/DON'T guidance | Process items incomplete (no test, no linter) |

**Pages using TorchViz3D and their Canvas counts:**

| Page | TorchViz3D instances | WebGL contexts | Loading fallback |
|------|------------------------|----------------|------------------|
| `/demo` | 2 (expert + novice) | 2 | ❌ No |
| `/replay/[sessionId]` | 1–2 (current + optional comparison) | 1–2 | ❌ No |
| `/dev/torch-viz` | 1 | 1 | ✅ Yes |

**Example broken flows:**
1. Developer saves code during dev → HMR remounts components → `forceContextLoss()` runs on unmount → Console shows "Context Lost" consistently on every hot reload.
2. User opens `/demo` with 2 TorchViz3D instances → On low-end GPU or with other tabs open → Context limit exceeded → White or black screen.
3. User switches tab while viewing replay → Browser revokes WebGL context → User returns → Overlay may not reliably show depending on timing.
4. User navigates Demo → Replay → Demo → Old Canvases may not dispose before new ones mount → Context accumulation risk.

**Technical gaps:**
- Demo and Replay pages lack `loading` fallback for TorchViz3D dynamic import (only dev/torch-viz has it).
- No centralized tracking of Canvas count across pages; each page independently decides instance count.
- No automated test verifying single-instance or 1–2 instance constraint.
- HMR-triggered context loss is expected per docs but produces noisy, alarming console output.
- No lint or code-review automation to warn when >2 Canvas imports on a page.

---

## Desired Outcome

**User-facing changes:**
- User sees a predictable "WebGL context lost — Refresh to restore 3D view" overlay whenever context is lost, on every page with 3D content.
- User sees a loading state ("Loading 3D…") while TorchViz3D bundle loads on demo and replay pages.
- User does not see white/black screen without an actionable message when context is lost.

**Technical changes:**
- Add `loading` fallback to all TorchViz3D `dynamic()` calls (demo, replay).
- Ensure TorchViz3D context-loss overlay is reliable and visible in all integration points.
- Reduce Canvas count where possible (e.g., evaluate shared Canvas / scissor pattern for demo and replay side-by-side views).
- Add test or assertion that demo/replay pages do not exceed 2 TorchViz3D instances.
- Document when/why "Context Lost" appears during HMR and that it is expected in dev.

**Acceptance criteria:**

1. **[ ]** Demo page shows loading fallback while TorchViz3D loads.
2. **[ ]** Replay page shows loading fallback while TorchViz3D loads.
3. **[ ]** When WebGL context is lost on any page, user sees the overlay "WebGL context lost — Refresh to restore 3D view" within 500ms.
4. **[ ]** Overlay is keyboard-accessible and screen-reader announced.
5. **[ ]** Demo page uses at most 2 TorchViz3D instances (or 1 if consolidated).
6. **[ ]** Replay page uses at most 2 TorchViz3D instances (or 1 if consolidated).
7. **[ ]** An automated test verifies demo page renders with ≤2 TorchViz3D (or equivalent constraint).
8. **[ ]** Documentation clarifies that "Context Lost" during HMR in dev is expected and not a regression.
9. **[ ]** No regression: existing TorchViz3D context-loss handlers remain and work when triggered.
10. **[ ]** Code review or lint guidance exists to warn when adding >2 TorchViz3D on a single page.

**Quality requirements:**
- Overlay works in Chrome, Firefox, Safari.
- Loading fallback does not cause layout shift (reserve h-64 area).
- No new console errors introduced; HMR context-loss message may still appear (documented).
- Performance: No slowdown from overlay logic.

---

## Scope Boundaries

**Explicitly in scope:**
- Adding `loading` fallback to demo and replay TorchViz3D dynamic imports.
- Verifying and fixing context-loss overlay visibility/reliability.
- Adding automated test for instance-count constraint on demo page.
- Updating `WEBGL_CONTEXT_LOSS.md` with HMR expectations and project-wide guidance.
- Ensuring all 3D pages follow the same pattern (loading + context-loss handling).

**Explicitly out of scope:**
- Refactoring to shared Canvas with scissor/multi-view (future optimization; document as option).
- Changing R3F or Three.js behavior (we work within current stack).
- Server-side or worker-based WebGL (not applicable).
- Suppressing HMR context-loss console message (browser/R3F behavior; document instead).
- Bulk export or other non-WebGL features.

---

## Known Constraints & Context

**Technical constraints:**
- Must use existing TorchViz3D component and R3F/Three.js stack.
- Must work with Next.js App Router and `dynamic(..., { ssr: false })`.
- Cannot change browser WebGL context limits (~8–16 per tab).
- Must support Chrome, Firefox, Safari (and mobile where demo is used).

**Business constraints:**
- MVP priority: reliability and correctness over new features.
- Time budget: TBD; small–medium effort preferred.

**Design constraints:**
- Must match existing overlay style (amber/cyan, Orbitron/JetBrains Mono).
- Loading fallback must fit existing layout (h-64, cyan theme where applicable).

---

## Related Context

**Similar features in codebase:**
- `my-app/src/app/dev/torch-viz/page.tsx` — Has loading fallback and single instance; reference implementation.
- `my-app/src/components/welding/TorchViz3D.tsx` — Contains context-loss handlers; extend or reuse.
- `documentation/WEBGL_CONTEXT_LOSS.md` — Primary reference; fix examples at lines 90–110 (onCreated handlers).

**Related documentation:**
- `LEARNING_LOG.md` — WebGL context limit incident; prevention strategy.
- `CONTEXT.md` — WebGL limits pattern; `.cursorrules` 3D section.

**External references:**
- [WebGL Context Limits — Stack Overflow](https://stackoverflow.com/questions/41919341/is-there-a-limit-to-the-number-of-three-webglrenderer-instances-in-a-page)
- [R3F Context Lost Discussion #2109](https://github.com/pmndrs/react-three-fiber/discussions/2109)
- [R3F Canvas onCreated for context events](https://github.com/pmndrs/react-three-fiber/issues/3206)

**Dependencies:**
- None (can start immediately).

---

## Open Questions & Ambiguities

1. **When exactly does "consistent" context loss occur?**
   - Why unclear: User said "throughout the project" but not specific triggers (HMR, tab switch, load, mobile).
   - Impact: Prioritization (HMR vs production vs mobile).
   - Current assumption: Address all triggers — loading, overlay reliability, instance count; document HMR as expected.

2. **Is overlay ever failing to show when context is lost?**
   - Why unclear: No explicit report of overlay not appearing.
   - Impact: If overlay is broken, that is critical; if not, focus on prevention.
   - Current assumption: Verify overlay logic and ensure it is not hidden by z-index or conditional render bugs.

3. **Should we consolidate demo/replay to 1 Canvas (scissor) instead of 2?**
   - Why unclear: 2 instances is within limit per docs; consolidation is more work.
   - Impact: Reduces context count; adds complexity.
   - Current assumption: Stay at 2 for now; document scissor as future optimization if issues persist.

4. **Does navigation (page transitions) leak contexts?**
   - Why unclear: Next.js unmount behavior; R3F dispose on unmount.
   - Impact: Could explain accumulation over multiple navigations.
   - Current assumption: Add disposal verification if exploration finds evidence of leaks.

---

## Initial Risk Assessment

1. **HMR noise in dev**
   - Why risky: Developers may treat "Context Lost" during HMR as a bug.
   - Impact: Wasted debugging time; confusion.
   - Likelihood: High (HMR runs frequently).

2. **Overlay visibility / z-index**
   - Why risky: Overlay might be behind other UI (ErrorBoundary, modals).
   - Impact: User sees white screen with no actionable message.
   - Likelihood: Low–Medium (depends on page structure).

3. **Mobile / low-end GPU**
   - Why risky: 2 Canvases + Environment + shadows may exceed GPU memory on some devices.
   - Impact: Context loss on specific devices; demo/replay unusable.
   - Likelihood: Medium (unknown device mix).

4. **Testing WebGL in jsdom**
   - Why risky: TorchViz3D is mocked in tests; instance-count test may not catch real violations.
   - Impact: False confidence if test is trivial.
   - Likelihood: Low (can test structure/count without real WebGL).

5. **Regression in existing handlers**
   - Why risky: Changing TorchViz3D or dynamic imports could break current overlay.
   - Impact: Overlay stops working where it worked before.
   - Likelihood: Low (changes are additive).

---

## Classification & Metadata

**Type:** bug  
**Priority:** high  
**Effort:** medium (8–16 hours)  
**Category:** frontend

---

## Strategic Context

**Product roadmap alignment:**
- Supports MVP reliability goal: "No silent failures; predictable behavior."
- Enables: Confident demo/replay on varied devices (laptop, tablet, mobile).
- Addresses: Known pain point documented in `LEARNING_LOG.md` and `WEBGL_CONTEXT_LOSS.md`.

**User impact:**
- Frequency: Affects every session with 3D content; developers every HMR.
- User segment: All users viewing demo or replay; developers during dev.
- Satisfaction impact: Reduces confusion and "broken" perception; clear messaging when recovery is needed.

**Technical impact:**
- Code health: Improves consistency (loading, overlay) across pages.
- Team velocity: Prevents recurring context-loss debugging; clear docs.
- Tech debt: Reduces (standardized pattern) or neutral.
