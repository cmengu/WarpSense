# Development Learning Log

**Purpose:** Document mistakes, solutions, and lessons learned to prevent repeating the same errors. Feed lessons to AI tools.  
**For AI Tools:** Reference this file with `@LEARNING_LOG.md` when implementing 3D/WebGL features.  
**For `.cursorrules`:** Check LEARNING_LOG.md for anti-patterns, required patterns, and past incidents before generating code.

**Last Updated:** 2025-02-17  
**Total Entries:** 5 incidents + Lessons & Reflections

**Metal plane clipping (2025-02-16):** Y-coordinates were scattered across TorchWithHeatmap3D; metal could clip through torch. Fix: centralize all workpiece/ring/grid/shadows Y in `welding3d.ts` with explicit constraint `metal_surface_max_Y < weld_pool_center_Y`. See `my-app/src/constants/welding3d.ts`.

**Color sensitivity (2025-02-16):** Heatmap shader now uses stepped gradient (0–500°C, 10°C per visible step). `heatmapShaderUtils.ts` provides TS mirror for unit tests. See `unified-torch-heatmap-replay-plan.md`.

**ThermalPlate WebGL lifecycle (2025-02-16):** Never allocate DataTexture or ShaderMaterial in `useMemo` — use `useEffect` with cleanup. `useMemo` is for pure computations; side effects (GPU resources) violate React rules and cause leaks in Strict Mode. See Round 1 review (.cursor/review-round1-output.md).

**Unified torch+heatmap (2025-02-16):** TorchWithHeatmap3D replaces separate TorchViz3D + HeatmapPlate3D. One Canvas: torch + thermally-colored metal. Replay/demo use this; HeatmapPlate3D kept for dev/standalone only.

**WWAD macro-analytics (2025-02-17):** Supervisor dashboard built orthogonally to micro-feedback — aggregate session data only, no frame/3D coupling. Migration `score_total` nullable + backfill; export with truncation logging.

---

## Quick Reference

| Date | Title | Category | Severity |
|------|-------|----------|----------|
| 2025-02-17 | WWAD Macro-Analytics (Supervisor Dashboard) | Backend / Architecture | 🟢 Medium |
| 2025-02-16 | Metal Plane Clipping Through Torch | Frontend / 3D | 🟢 Medium |
| 2025-02-16 | Unified Torch + Thermal Metal (Replay) | Frontend | 🟢 Medium |
| 2025-02-16 | WebGL Context Lost — Project-Wide Mitigations | Frontend / Performance | 🟡 High |
| 2025-02-12 | WebGL Context Lost — White Screen | Frontend / Performance | 🟡 High |

---

## ⚡ Performance & Optimization

### 📅 2025-02-12 — WebGL Context Lost / White Screen on /dev/torch-viz

**Category:** Frontend / Performance  
**Severity:** 🟡 High

**What Happened:**
The `/dev/torch-viz` page showed a white screen instead of the 3D torch visualization. Console reported `THREE.WebGLRenderer: Context Lost.`

**Impact:**
- Dev demo page unusable — users saw white screen
- Replay page (1–2 instances) worked; dev page (6 instances) failed
- No user-facing message — only console error

**Root Cause:**
- **Technical:** Browsers limit WebGL contexts to ~8–16 per tab. Each `<Canvas>` in react-three-fiber creates one. Six TorchViz3D instances = 6 contexts; combined with HMR or other tabs, the limit was exceeded.
- **Process:** No check for WebGL context limits when designing multi-instance 3D layouts.
- **Knowledge gap:** Unfamiliar with browser WebGL context limits and R3F's one-context-per-Canvas behavior.

**The Fix:**

```tsx
// ❌ BEFORE — 6 Canvases exhausted WebGL context limit
<div className="grid grid-cols-2 gap-4">
  <TorchViz3D angle={45} temp={250} />
  <TorchViz3D angle={45} temp={400} />
  <TorchViz3D angle={45} temp={520} />
  <TorchViz3D angle={30} temp={450} />
  <TorchViz3D angle={45} temp={450} />
  <TorchViz3D angle={60} temp={450} />
</div>

// ✅ AFTER — 1 instance + loading fallback + context-loss handler
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false, loading: () => <div>Loading 3D…</div> }
);
// In TorchViz3D: onCreated adds webglcontextlost listener; overlay when lost
<div><TorchViz3D angle={45} temp={450} label="LIVE PREVIEW" /></div>
```

**Prevention Strategy:**

**Code Level:**
- ✅ DO: Limit to 1–2 Canvas instances per page; use scissor/multi-view if more views needed
- ✅ DO: Add `webglcontextlost` / `webglcontextrestored` handlers and show "Refresh to restore" overlay
- ✅ DO: Add `loading` fallback to dynamic 3D imports
- ✅ DO: Use 1024×1024 shadow maps instead of 2048×2048 when possible
- ❌ DON'T: Render 6+ independent Canvases on one page
- ❌ DON'T: Ignore context loss — surface it to the user

**Process Level:**
- [x] Add to code review: "Does this page use multiple 3D Canvases? Count them."
- [x] Add test: Demo and Replay pages have tests verifying ≤2 TorchViz3D instances
- [x] Lint/comment guidance: src/constants/webgl.ts + WEBGL_CONTEXT_LOSS.md checklist

**AI Prompting Guidance:**
When implementing 3D / React Three Fiber features:
> "Use at most 1–2 Canvas instances per page. Browsers limit WebGL contexts (~8–16 per tab). Add webglcontextlost listeners and show a 'Refresh to restore' overlay. See documentation/WEBGL_CONTEXT_LOSS.md and @LEARNING_LOG.md."

**Good Prompt Example:**
> "Add a TorchViz3D 3D component to the compare page. Follow LEARNING_LOG.md WebGL patterns: single Canvas per view, context-loss overlay, loading fallback. Check documentation/WEBGL_CONTEXT_LOSS.md."

**Warning Signs:**
- White or blank 3D canvas → likely context loss
- `THREE.WebGLRenderer: Context Lost` in console → confirmed
- [HMR] connected followed by context lost → common during dev; new mount should work
- Multiple Canvas components in same route → high risk of hitting limit

**Related:**
- `documentation/WEBGL_CONTEXT_LOSS.md` — Full error reference and fix examples

---

### 📅 2025-02-16 — WebGL Context Lost — Project-Wide Mitigations

**Category:** Frontend / Performance  
**Severity:** 🟡 High

**What Was Done:**
Hardened TorchViz3D overlay for visibility (z-[100], isolate), added demo instance-count test, ESLint rule enforcing ≤2 TorchViz3D per page, HMR documentation, manual overlay verification procedure, code review checklist.

**Key Changes:**
- Overlay: `isolate` on wrapper, `z-[100]` to beat parent stacking contexts
- Tests: Demo and replay pages both assert ≤2 TorchViz3D instances
- ESLint: Custom rule `max-torchviz/max-torchviz3d-per-page` fails build when page has >2 instances
- Docs: HMR section, manual verification procedure, code review checklist in WEBGL_CONTEXT_LOSS.md

**Process Level (updated):**
- ESLint rule for instance count
- Manual overlay verification doc
- Code review checklist for 3D/WebGL

**References:**
- `.cursor/plans/webgl-context-loss-project-wide-plan.md`
- `documentation/WEBGL_CONTEXT_LOSS.md`

---

## 🎨 Frontend / 3D Thermal Visualization

### 📅 2025-02-16 — Unified Torch + Thermal Metal (Replay)

**Category:** Frontend  
**Severity:** 🟢 Medium

**What Was Done:**
Integrated 3D heatmap on metal into replay/demo instead of a separate heatmap component. TorchWithHeatmap3D renders torch + thermally-colored workpiece in one Canvas. Heat "travels" through the metal as frames advance (0–500°C). Color sensitivity tuned so 5–10°C differences are visible.

**Impact:**
- Single 3D view per session (torch + metal), no separate HeatmapPlate3D
- 10°C per visible step (THERMAL_COLOR_SENSITIVITY=10); for finer steps use 5
- WebGL instance count stays ≤2 per page (TorchWithHeatmap3D replaces TorchViz3D + HeatmapPlate3D)

**Patterns:**

```tsx
// ❌ BEFORE — separate torch and heatmap (2 Canvas-equivalent components)
<TorchViz3D angle={45} temp={450} />
<HeatmapPlate3D frames={frames} />

// ✅ AFTER — unified component (1 Canvas, torch + thermal metal)
<TorchWithHeatmap3D
  frames={thermalFrames}
  maxTemp={THERMAL_MAX_TEMP}
  minTemp={THERMAL_MIN_TEMP}
  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
/>
```

**Prevention:**
- ✅ DO: Use TorchWithHeatmap3D for replay/demo when thermal data exists
- ✅ DO: Pass colorSensitivity (5–10) so small temp changes are visible; 10 = 50 steps over 0–500°C
- ✅ DO: Keep heatmapShaderUtils.ts in sync with heatmapFragment.glsl.ts for tests
- ❌ DON'T: Add separate HeatmapPlate3D alongside TorchViz3D on same page (inflates WebGL count)

**AI Guidance:**
```
When adding thermal visualization to replay/demo:
"Use TorchWithHeatmap3D (not TorchViz3D + HeatmapPlate3D). Pass frames, maxTemp/minTemp, colorSensitivity from constants/thermal.ts. For 5°C visibility set THERMAL_COLOR_SENSITIVITY=5."
```

**References:**
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
- `my-app/src/constants/thermal.ts` — THERMAL_COLOR_SENSITIVITY, THERMAL_MAX_TEMP
- `.cursor/plans/unified-torch-heatmap-replay-plan.md`

---

### 📅 2025-02-16 — Metal Plane Clipping Through Torch

**Category:** Frontend / 3D  
**Severity:** 🟢 Medium

**What Happened:**
Metal workpiece, angle ring, grid, and ContactShadows used hardcoded or inconsistent Y-positions. Metal surface could intersect the weld pool; metal clipped through the torch during rotation.

**Impact:**
- Visual artifact: metal plane clipping through torch
- Inconsistent depth ordering when rotating view
- No enforcement of metal-below-torch constraint

**Root Cause:**
- **Technical:** Y-coordinates scattered across TorchWithHeatmap3D; workpiece, ring, grid, shadows each had different/ad-hoc values. No single source of truth.
- **Process:** No central constraint asserting `metal_surface_max_Y < weld_pool_center_Y`.

**The Fix:**

```tsx
// ❌ BEFORE — scattered Y values
<group position={[0, -0.85, 0]}>  // ad-hoc
<mesh position={[0, -0.84, 0]}>   // different ad-hoc
<ContactShadows position={[0, -0.84, 0]} />
```

```tsx
// ✅ AFTER — single source of truth
// welding3d.ts: WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
// Constraint: metal_surface_max_Y (-0.35) < WELD_POOL_CENTER_Y (-0.2), gap ≥ 0.15
<group position={[0, WORKPIECE_GROUP_Y, 0]}>
<mesh position={[0, ANGLE_RING_Y, 0]}>
<ContactShadows position={[0, CONTACT_SHADOWS_Y, 0]} />
```

**Prevention:**
- ✅ DO: Use `welding3d.ts` for all workpiece/ring/grid/shadows Y positions
- ✅ DO: Assert `metal_surface_max_Y < WELD_POOL_CENTER_Y` and `gap >= 0.1` in tests
- ✅ DO: Keep weld pool Y (torch-internal) separate; only metal-side uses welding3d
- ❌ DON'T: Hardcode Y values in TorchWithHeatmap3D or related components
- ❌ DON'T: Change MAX_THERMAL_DISPLACEMENT without checking HeatmapPlate3D / ThermalPlate

**AI Guidance:**
```
When modifying 3D welding scene Y-positions:
"Use constants from welding3d.ts (WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y). Never hardcode Y in components. Constraint: metal_surface_max_Y < weld_pool_center_Y. See LEARNING_LOG.md metal plane clipping entry."
```

**References:**
- `my-app/src/constants/welding3d.ts`
- `.cursor/plans/metal-heatmap-y-position-clipping-fix-plan.md`
- `.cursor/issues/metal-heatmap-y-position-clipping-torch.md`

---

## 📊 Backend / Architecture

### 📅 2025-02-17 — WWAD Macro-Analytics (Supervisor Dashboard)

**Category:** Backend / Architecture  
**Severity:** 🟢 Medium

**What Was Done:**
Implemented supervisor-level macro analytics (WWAD) orthogonally to the MVP. New aggregate API (`/api/sessions/aggregate`), KPI tiles, trend chart, calendar heatmap, and CSV export. Session-level aggregation only — no frame data or 3D coupling.

**Impact:**
- Supervisors see team KPIs, trends, and activity at a glance
- Fully decoupled from TorchViz3D, HeatmapPlate3D, micro-feedback logic
- Adding/changing macro features does not touch replay or scoring

**Root Cause (Design Decision):**
- MVP dashboard was tightly coupled to frame-level + 3D visualization
- Macro analytics needed team/line/shift trends without reworking micro-feedback

**Patterns:**

```python
# ❌ BEFORE — macro features would touch frame-level or 3D
# Any change to scoring or visualization could break dashboard

# ✅ AFTER — orthogonal design
# Aggregate API: session → score + metrics → trend/KPI dashboard
# No per-frame data, no WebGL, no micro-feedback dependency
```

**Database pattern:**

```sql
-- ✅ DO: Add nullable + default, backfill separately
ALTER TABLE sessions ADD COLUMN score_total NUMERIC DEFAULT NULL;
-- Run backfill script; then optionally add NOT NULL + constraint
```

**Prevention:**
- ✅ DO: Keep macro analytics on session-level aggregation only
- ✅ DO: Use nullable + backfill for new columns on existing tables
- ✅ DO: Log truncation and export failures; handle empty/null edge cases
- ❌ DON'T: Couple supervisor dashboards to frame-level or 3D components
- ❌ DON'T: Add NOT NULL to new columns without backfill path

**AI Guidance:**
```
When adding macro/aggregate features:
"Use session-level data only. Do not depend on frame extraction, 3D components, or micro-feedback. New columns: add nullable first, backfill, then optionally constrain. See LEARNING_LOG.md WWAD entry."
```

**References:**
- `backend/services/aggregate_service.py`, `backend/routes/aggregate.py`
- `my-app/src/app/(app)/supervisor/page.tsx`
- `backend/scripts/backfill_score_total.py`, `backend/alembic/versions/003_add_score_total.py`

---

## 📋 Lessons & Reflections

> **Scope:** WebGL context loss hardening, Docker one-click deploy, premium landing page, demo page refactor, WWAD macro-analytics.  
> **Date:** 2025-02-17

### What Worked Well

1. **Orthogonal macro analytics (WWAD)** — Supervisor dashboard built on session aggregation only; zero coupling to frame-level data, 3D components, or micro-feedback. New features (KPIs, heatmap, export) added without touching replay or scoring. Migration used nullable `score_total` + separate backfill script.

2. **Layered WebGL mitigation** — Documentation (WEBGL_CONTEXT_LOSS.md) → code (overlay, handlers) → tests (instance count) → ESLint (max-torchviz rule). Each layer catches different failure modes. AI tools can reference one source.

3. **Route groups for layout separation** — `(marketing)` vs `(app)` eliminated conditional `isLanding` logic in AppNav. Layout structure controls nav visibility; no branching in components.

4. **One-click deploy script with fail-fast checks** — Port pre-check, Docker V1/V2 resolution, per-service health wait, secure `.env` (umask 077, openssl rand). Script exits early with clear messages instead of cryptic Docker errors.

5. **Idempotent seed script** — `seed_demo_data.py` can run multiple times; "already present" handling avoids deploy failures on re-run. Kept seed in deploy.sh exec (not backend entrypoint) so backend CMD stays simple.

6. **Proxy-based Framer Motion mock** — Jest tests need to filter `style` prop (MotionValues are invalid in DOM). Proxy mock that strips/filters `style` enables testing animated components without DOM errors.

7. **Backwards compatibility via re-exports** — Keeping `/landing` as re-export of `(marketing)/page` avoided breaking existing links while canonical route moved to `/`.

### What Didn't Work or Was Challenging

1. **Six TorchViz3D instances** — Initial demo layout exhausted WebGL context limit. No prior check for browser limits when designing multi-instance 3D layouts. Recovery required layout redesign + overlay + tests.

2. **Remote deployment requires rebuild** — `NEXT_PUBLIC_API_URL` is build-time in Next.js. Changing server IP means rebuild + redeploy. API proxy (Phase 1) was deferred; current approach works for localhost and single-server trials only.

3. **Seeding failure is non-fatal** — If seed fails (schema/import issue), deploy continues. Demo pages may show empty data. No automated verification that `sess_expert_001` exists; manual curl check required.

4. **Safari transform glitches** — Grid/parallax effects caused visual glitches. Required `perspective` on parent, `rotateX` on child workaround. Cross-browser 3D/CSS testing is essential.

5. **Framer Motion + Jest** — MotionValues in `style` prop fail when passed to DOM in tests. Required custom mock; not obvious until tests failed.

### Patterns to Reuse

1. **Orthogonal macro analytics** — Build supervisor/management dashboards on session-level aggregation only. No frame data, no 3D, no micro-feedback. New columns: nullable + backfill, then optionally constrain.

2. **3D/WebGL page pattern** — Limit 1–2 Canvas per page; add `webglcontextlost` handlers + overlay; use `dynamic(..., { ssr: false, loading })`; enforce with ESLint.

3. **Deploy script pattern** — Prerequisite checks (ports, Docker) → generate secrets → build → up → health wait → optional seed. Use `$COMPOSE` for V1/V2 compatibility.

4. **Env fallback with trim** — `process.env.X?.trim() || '/fallback'` handles empty string (common when env var is set but empty). Prefer explicit fallbacks over undefined.

5. **Route group layout pattern** — One layout per route group; no conditional "if marketing, hide nav" inside components. Layout composition at route level.

### Gotchas & Edge Cases

- **HMR + context lost** — Expected during dev; R3F calls `forceContextLoss()` on unmount. Don't file as bug; add to onboarding.
- **Empty env string** — `NEXT_PUBLIC_X=""` yields `""` not `undefined`. Use `.trim()` before fallback.
- **Docker healthcheck deps** — Alpine has no curl/wget. Use `python -c "urllib.request.urlopen(...)"` or `node -e "require('http').get(...)"` for health checks.
- **Safari stacking/transform** — Overlay needed `isolate` and `z-[100]` to beat parent stacking contexts. Test overlay visibility in Safari.

### Process Improvements for Next Time

- [ ] **Pre-3D work:** Check LEARNING_LOG.md and WEBGL_CONTEXT_LOSS.md before adding Canvas components.
- [ ] **Deploy validation:** Run `./deploy.sh` on clean Linux host (e.g. DigitalOcean droplet) before considering deploy "done".
- [ ] **Seed verification:** Add deploy.sh poll for `sess_expert_001`; fail deploy if missing after ~50s.
- [ ] **Cross-browser checklist:** Chrome, Firefox, Safari for any 3D/CSS transform work.

### Technical Insights

- Browsers limit ~8–16 WebGL contexts per tab; each R3F `<Canvas>` = 1 context.
- `NEXT_PUBLIC_*` in Next.js are inlined at build time; no runtime override without rebuild.
- Docker Compose V2 uses `docker compose` (plugin); V1 uses `docker-compose` (standalone). Resolve and use `$COMPOSE` throughout scripts.
- ESLint custom rules can enforce domain constraints (e.g. max instances per page) and fail CI.

### Mistakes & How to Avoid

| Mistake | Avoidance |
|---------|-----------|
| Assumed 6 Canvases would work | Count Canvas/3D instances before designing layout; check browser limits. |
| No context-loss handling | Always add `webglcontextlost` listener and user-facing overlay. |
| Env fallback without trim | Use `.trim()` so empty string triggers fallback. |
| Healthcheck with missing deps | Use runtime-available tools (python urllib, node http) not curl/wget. |
| Seed in entrypoint vs script | Prefer deploy.sh exec for clarity; add verification step if demo data is critical. |

### Additional Insights (WebGL / Demo / Tooling)

- **Incident → Doc → Automation** — When something breaks: root-cause in a doc, add fix examples, add tests + lint enforcement. Don't stop at "fixed in code."
- **Single source of truth** — `src/constants/webgl.ts` exports `MAX_TORCHVIZ3D_PER_PAGE`; ESLint and tests reference it. `src/constants/welding3d.ts` exports Y-coordinates for workpiece/ring/grid/shadows; all 3D metal geometry uses it. Change in one place.
- **Demo vs replay contracts** — Demo uses in-memory `Session`; replay fetches from API. Both must produce frames compatible with `extractHeatmapData`, `extractAngleData`, `getFrameAtTimestamp`.
- **ESLint rule scope** — Rule must exclude `__tests__` and `/app/dev/`. Windows paths need `replace(/\\/g, '/')`. Aliased imports (`<T />`) not detected.
- **1024×1024 shadow maps** — Reduces GPU memory pressure vs 2048×2048. Use `@react-three/scissor` for >2 views (one Canvas, scissor regions).
- **Dev-only overlay test** — Add `/dev/context-loss-test` that toggles `setContextLost(true)` for 2s; no need to exhaust contexts for QA.

---

## Maintenance

**Daily:** Add entries when fixing bugs (5 min)  
**Weekly:** Review with team, update .cursorrules  
**Monthly:** Analyze trends, update checklist

---

## Related Docs

| File | Purpose |
|------|---------|
| `.cursor/context/project-context.md` | What exists, patterns |
| `.cursorrules` | AI configuration |
| `README.md` | Project setup |

---

**Remember:** Every mistake documented is future productivity gained. Start small, be consistent. 🚀
