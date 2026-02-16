# [Feature] Unified 3D Torch + Thermal Metal — Replace Separate Heatmap with Heat-on-Metal in Replay

---

## Phase 0: Mandatory Pre-Issue Thinking Session

### A. Brain Dump (5+ minutes)

**Raw thinking — stream of consciousness:**

The user explicitly does NOT want a separate 3D heatmap component. They want the heatmap ON THE METAL in the same view as the dynamic 3D torch. So instead of having TorchViz3D (torch + flat gray workpiece) AND HeatmapPlate3D (separate warped thermal plate) side by side, they want ONE view: torch above metal, and the metal surface itself shows the thermal distribution. That's a consolidation — fewer Canvases, more coherent UX.

The second major request: color sensitivity is too low. Current gradient uses 50°C anchors (heatmapData.ts) and 4 broad bands in the HeatmapPlate3D fragment shader (t<0.2, t<0.5, t<0.8, t>0.8). In welding, 5–10°C matters — even small deviations indicate problems. We need to make 5–10° differences visually distinguishable. That means either: (a) finer gradient anchors (every 5–10°C instead of 50°C), or (b) a perceptual color scale that amplifies small differences, or (c) both. The range 0–500°C with 5° steps = 100 distinguishable levels. Human color perception might not handle 100 distinct hues; we might need a combination of hue + saturation + brightness to encode that.

Third: "heat sort of travel through the metal, heating it up from 0 degrees to 500 degrees." Two interpretations: (1) Temporal: as playback runs, we see the metal heat up over time — heat accumulates and dissipates. That would require carrying thermal state forward/backward, possibly using heat_dissipation_rate. (2) Spatial: at any moment, we see heat spread across the metal (center hot, edges cold) — that's what we already do with 5-point interpolation. Or (3) Both: temporal buildup AND spatial spread. The phrase "heating it up" suggests temporal. Our thermal data is sparse (5 Hz); we have extractCenterTemperatureWithCarryForward for continuity. We might need a similar carry-forward for the full 5-point spatial field — or interpolate between thermal frames for smooth animation.

WebGL context: Currently replay = 2 TorchViz3D + 1 HeatmapPlate3D = 3 Canvases. If we merge heatmap into TorchViz3D, we remove HeatmapPlate3D. Replay would have 2 TorchViz3D only = 2 Canvases. That's better for context limits! Demo already has 2 TorchViz3D + 1 HeatmapPlate3D (expert only; novice has HeatMap). Merging would reduce Canvas count.

Technical approach: TorchViz3D's workpiece is currently a flat plane with meshStandardMaterial. We'd replace it with a subdivided plane (like HeatmapPlate3D's 100×100) that samples a temperature texture, with vertex displacement and fragment color from temp. We'd need to pass thermal frames into TorchViz3D — so TorchViz3D props become angle, temp, label, AND frames, activeTimestamp. Or we could create a new component TorchViz3DWithThermalMetal that extends TorchViz3D. Or refactor TorchViz3D to optionally accept thermal data and render thermal workpiece when provided.

Data flow: Replay page has thermal_frames, currentTimestamp. It passes to HeatmapPlate3D. It also passes angle, temp to TorchViz3D. To unify, we'd pass frames + activeTimestamp to TorchViz3D as well, and TorchViz3D would render thermal workpiece. HeatmapPlate3D gets removed from replay (and demo expert column).

Fine gradient: heatmapData.ts has TEMP_COLOR_ANCHORS every 50°C. For 5–10° sensitivity, we need 50–100 anchors from 0–500°C. That's a lot. Alternative: use a continuous function in the shader, e.g. smooth ramp with high derivative in the critical range. Or use a texture as a LUT (lookup table) — 512 pixels for 0–500°C gives ~1° per pixel. Or a parametric gradient with adjustable "stretch" for the 400–500°C band where small differences matter most.

Who is affected: Replay users, demo users. Compare page uses HeatMap only for session A/B/delta — no TorchViz3D there. So compare is out of scope.

What could go wrong: TorchViz3D gets more complex. Props bloat. Thermal interpolation + shader in TorchViz3D means we're merging two components' logic. Testing surface grows. Also: TorchViz3D currently has a small workpiece (3×3 units); HeatmapPlate3D has a larger plate (10×10). Scale and camera framing might need adjustment so the thermal detail is visible.

---

### B. Question Storm (20+ questions)

1. Should we merge HeatmapPlate3D into TorchViz3D, or create a new TorchViz3DWithThermalMetal component?
2. When thermal_frames is empty, should TorchViz3D fall back to flat gray workpiece (current behavior)?
3. For 5–10°C sensitivity: use 50–100 gradient anchors, or a continuous parametric function, or a LUT texture?
4. Should the gradient be linear in temp, or perceptual (e.g. amplify 400–500°C band)?
5. What is "heat travel" — temporal accumulation over playback, or just spatial spread at current frame?
6. If temporal: do we have backend support for accumulated thermal state, or must we synthesize it?
7. Does heat_dissipation_rate help model temporal cooling between thermal frames?
8. Should we interpolate thermal texture between 5Hz thermal frames for 100fps playback smoothness?
9. Workpiece size: keep TorchViz3D's 3×3 or use HeatmapPlate3D's 10×10 for more thermal detail?
10. Grid resolution: 100×100 vertices (like HeatmapPlate3D) or less to match smaller workpiece?
11. What happens on compare page — no TorchViz3D, so no change there?
12. Demo: expert has HeatmapPlate3D + TorchViz3D; after merge, expert gets TorchViz3D with thermal metal only?
13. Demo novice: currently HeatMap only (no thermal frames in demo? Need to check demo-data).
14. Do we deprecate HeatmapPlate3D entirely, or keep it for a "heatmap-only" view option?
15. ESLint max-torchviz rule — does it need to change if we remove HeatmapPlate3D?
16. MAX_CANVAS_PER_PAGE: would drop from 3 to 2 on replay. Is that a constraint relaxation?
17. Interpolation: same 5-point IDW as HeatmapPlate3D, or different?
18. Temperature range: user said 0–500°C; current system uses 20–600°C. Align to 0–500?
19. Vertex displacement: keep thermal warping (bulge when hot) or flatten for simpler view?
20. Accessibility: 3D thermal metal is harder to describe than 2D heatmap. Fallback?
21. Performance: 100×100 plane in TorchViz3D — same as HeatmapPlate3D. Acceptable?
22. Do we need heat "animation" (interpolate between frames) or is frame-accurate enough?
23. Which thermal snapshot distance (10, 20, 30mm etc.) for the workpiece? Same as HeatmapPlate3D (first)?
24. Torch position: currently fixed above center. Does it need to align with "hottest point" from thermal?

---

### C. Five Whys Analysis

**Problem:** User sees separate 3D torch view and separate 3D heatmap; color changes are too coarse to see 5–10°C variations; wants heat to "travel" on the metal.

**Why #1:** Why is this a problem?
- **Answer:** Split views create cognitive load; user must mentally correlate torch and heat. Coarse colors hide critical temperature nuances. Missing temporal heat propagation reduces understanding of weld behavior.

**Why #2:** Why is that a problem?
- **Answer:** In safety-adjacent welding, 5–10°C can indicate overheating or poor heat control. Industrial users expect to see subtle thermal gradients. Without temporal propagation, the visualization feels static and disconnected from real welding.

**Why #3:** Why is that a problem?
- **Answer:** Product positioning is "industrial-grade, correctness, explainability." A visualization that obscures 5–10° differences undermines trust. Separate torch and heatmap feel like separate tools, not one integrated weld view.

**Why #4:** Why is that a problem?
- **Answer:** We're underutilizing our thermal data and 3D capabilities. We have 5-point thermal and a 3D torch; putting heat on the metal unifies them. Coarse gradients waste the precision of our sensor data.

**Why #5:** Why is that the real problem?
- **Answer:** The visualization layer has not evolved to (a) unify torch and thermal into one coherent scene, (b) expose fine temperature differences (5–10°C) that matter for weld quality, and (c) convey thermal dynamics (heat buildup/dissipation) over time. Root cause: fragmented components and coarse color scaling.

**Root cause identified:** Visualization architecture keeps torch and thermal separate; color scaling uses 50°C steps that obscure clinically significant 5–10°C differences; no temporal thermal propagation model in the UI.

---

## 1. Title

**[Feature] Unified 3D Torch + Thermal Metal — Replace Separate Heatmap with Heat-on-Metal in Replay**

**Title Quality Checklist:**
- [x] Starts with type tag
- [x] Specific (unified, thermal on metal, replace)
- [x] Under 100 characters
- [x] No jargon
- [x] Action-oriented

---

## 2. TL;DR

**Executive Summary (5–7 sentences):**

Users view replay with a 3D torch (TorchViz3D) and a separate 3D heatmap plate (HeatmapPlate3D) in different panels, forcing mental correlation between torch position and thermal distribution. The thermal color gradient uses 50°C steps, making 5–10°C variations invisible — yet in welding, 5–10° off is clinically significant (overheating, poor control). The user wants one unified view: the dynamic 3D torch above metal where the metal surface itself shows thermal distribution, with fine-grained color sensitivity (5–10°C distinguishable) and visible heat propagation as the weld progresses. Currently, HeatmapPlate3D and TorchViz3D are separate; the workpiece in TorchViz3D is a flat gray plane with no thermal data. We should replace that workpiece with a thermal mesh (interpolated 5-point data, vertex displacement, temp-to-color) and remove the standalone HeatmapPlate3D from replay and demo. Additionally, refine the temperature-to-color gradient to expose 5–10°C differences (e.g., 5–10°C anchors or perceptual stretch) and explore temporal thermal propagation so heat visibly "travels" through the metal. This aligns with our industrial positioning and data integrity goals: one source of truth, exact replays, no guessing. Effort: medium-large (16–24 hours) given shader tuning, gradient redesign, and optional temporal model.

---

## 3. Current State (What Exists Today)

### A. What's Already Built

**UI Components:**

1. **TorchViz3D** — `my-app/src/components/welding/TorchViz3D.tsx`
   - **What it does:** Renders 3D torch + weld pool with angle and temperature-driven weld pool color. Workpiece is a flat 3×3 plane with `meshStandardMaterial` color `#1a1a1a` — no thermal data.
   - **Current capabilities:** PBR, HDRI, OrbitControls, `angle`, `temp`, `label` props. Context-loss handler.
   - **Limitations:** Workpiece has no thermal distribution; no heat-on-metal.
   - **Dependencies:** R3F, Three.js, dynamic import.
   - **Props:** `angle: number`, `temp: number`, `label?: string`. No `frames` or `activeTimestamp`.

2. **HeatmapPlate3D** — `my-app/src/components/welding/HeatmapPlate3D.tsx`
   - **What it does:** Renders 3D metal plate (10×10, 100×100 grid) with thermal vertex displacement and temp→color. Separate Canvas. TorchIndicator cone above plate.
   - **Current capabilities:** 5-point IDW interpolation, custom shaders, OrbitControls.
   - **Limitations:** Separate from TorchViz3D; replay shows both side-by-side. Color gradient uses 4 broad bands (t<0.2, 0.5, 0.8, 1).
   - **Props:** `frames`, `activeTimestamp`, `maxTemp`, `plateSize`.

3. **HeatMap** — `my-app/src/components/welding/HeatMap.tsx`
   - CSS grid heatmap; used when no thermal_frames. Not in scope for merge.

**Data flow:**
```
Replay page:
  - TorchViz3D(angle, temp, label) — 2 instances (expert, novice)
  - HeatmapPlate3D(frames, activeTimestamp, maxTemp, plateSize) — 1 instance
  - Total Canvases: 3
```

**Shaders (HeatmapPlate3D):**
- `heatmapVertex.glsl.ts`: Samples `uTemperatureMap`, displaces vertices by `(temp/uMaxTemp)*uMaxDisplacement`.
- `heatmapFragment.glsl.ts`: `temperatureToColor(t)` with 4 bands; `t = clamp(temp/uMaxTemp, 0, 1)`.

**Color scaling:**
- `heatmapData.ts` — `TEMP_COLOR_ANCHORS` every 50°C (20, 70, 120, … 600). 13 steps over 580°C.
- HeatmapPlate3D shader — normalized t in [0,1]; 4 bands. A 50° change at 400°C ≈ t change of 50/600 ≈ 0.083 — subtle.
- For 5° at 400°C: t change = 5/600 ≈ 0.008 — nearly invisible with 4 bands.

**Thermal interpolation:**
- `thermalInterpolation.ts` — `interpolateThermalGrid(center, north, south, east, west, gridSize)` → 100×100 grid. IDW with power=2.

**Frame utilities:**
- `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` — used for TorchViz3D temp.
- Thermal at 5 Hz; carry-forward avoids flicker when thermal_snapshots missing.

**WebGL limits:**
- `MAX_TORCHVIZ3D_PER_PAGE = 2`, `MAX_CANVAS_PER_PAGE = 3`.
- Replay: 2 TorchViz3D + 1 HeatmapPlate3D = 3.

### B. Current User Flows

**Flow 1: Replay**
```
User loads /replay/[sessionId]
  → Two panels: (1) TorchViz3D (torch + flat gray metal), (2) HeatmapPlate3D (thermal plate)
  → User scrubs timeline
  → Torch angle/temp update in TorchViz3D; thermal plate updates in HeatmapPlate3D
Current limitation: Must look at two places; metal under torch has no thermal.
```

**Flow 2: Demo**
```
User loads /demo
  → Expert: TorchViz3D + HeatmapPlate3D
  → Novice: TorchViz3D + HeatMap (no thermal_frames in novice? Demo-data has thermal for expert)
Current limitation: Same split for expert; novice gets 2D heatmap.
```

### C. Technical Gaps Inventory

**Frontend gaps:**
- TorchViz3D workpiece does not accept thermal data.
- No fine (5–10°C) gradient in shaders or heatmapData.
- No temporal thermal propagation (heat accumulation/dissipation) in visualization.
- HeatmapPlate3D is a separate component; no integration path into TorchViz3D.

**Color scaling gaps:**
- 50°C anchors: 50° span ≈ 8% of 600°C range — too coarse.
- Shader 4 bands: 25% each — 5° = 0.8% of range, invisible.

---

## 4. Desired Outcome (What Should Happen)

### A. User-Facing Changes

**Primary User Flow:**
```
User loads replay/demo
  → Single view per session: 3D torch above metal
  → Metal surface shows thermal distribution (color + optional warp)
  → Color changes visibly for 5–10°C differences (e.g., 395° vs 405° distinguishable)
  → As playback runs, heat visibly propagates/heats up on metal (0°→500°C range)
  → No separate HeatmapPlate3D panel
Success state: One coherent thermal-torch visualization.
```

**UI Changes:**
1. **Modified TorchViz3D workpiece:** Replace flat gray plane with thermal mesh when `frames` and `activeTimestamp` provided.
2. **Remove HeatmapPlate3D** from replay and demo expert column.
3. **Optional thermal warp:** Vertex displacement on metal (like HeatmapPlate3D) or flat with color only (simpler).

**UX Changes:**
- Unified view: torch and heat in one scene.
- Fine color sensitivity: 5–10°C visible.
- Temporal heat propagation (clarify in scope).

### B. Technical Changes

**TorchViz3D modifications:**
- New optional props: `frames?: Frame[]`, `activeTimestamp?: number`, `maxTemp?: number`, `showThermalMetal?: boolean`.
- When `frames` and `showThermalMetal` and thermal_frames.length > 0: replace workpiece with thermal mesh (subdivided plane, shader material, temperature texture).
- Reuse: `interpolateThermalGrid`, `extractFivePointFromFrame`, `getFrameAtTimestamp`.

**New/modified shader:**
- Fine gradient: 5–10°C steps. Options: (a) 50–100 anchors in JS, pass as LUT texture; (b) parametric shader with adjustable sensitivity; (c) HSV-based: hue = temp, saturation = 1, value scaled for low-temp visibility.

**HeatmapPlate3D:**
- Remove from replay page.
- Remove from demo expert column (or keep as optional "heatmap-only" view — out of scope for Phase 1).
- Deprecate or delete file (or keep for compare page if ever added).

**Data model:** No backend changes. Use existing `Frame`, `ThermalSnapshot`, 5-point readings.

### C. Success Criteria (12+ Acceptance Criteria)

**User can:**
1. **[ ]** See thermal distribution on the metal surface in the same view as the 3D torch.
2. **[ ]** See color changes for 5–10°C temperature differences (e.g., 400° vs 410° visibly different).
3. **[ ]** Scrub timeline and see thermal metal update with active frame.
4. **[ ]** Orbit/zoom the unified torch+metal view (OrbitControls).
5. **[ ]** Not see a separate HeatmapPlate3D panel on replay (or demo expert).
6. **[ ]** See heat range 0–500°C represented (or 20–500°C per existing convention).

**System does:**
7. **[ ]** Interpolate 5-point thermal to grid and render on TorchViz3D workpiece when `frames` provided.
8. **[ ]** Use gradient with 5–10°C effective resolution (design TBD in exploration).
9. **[ ]** Fall back to flat gray workpiece when no thermal data.
10. **[ ]** Respect WebGL context limits (reduced Canvas count after merge).
11. **[ ]** Handle sparse thermal (5 Hz) with carry-forward or interpolation between frames.

**Quality:**
12. **[ ]** Performance: 60fps with thermal mesh in TorchViz3D.
13. **[ ]** Accessibility: `aria-label` on unified view; HeatMap fallback when 3D unavailable.

**Temporal heat propagation (optional/scoped):**
14. **[ ]** (If in scope) Heat visibly builds up and dissipates over playback — e.g. accumulated thermal state or interpolated frames.

### D. Detailed Verification (Top 5)

**Criterion 1: Thermal on metal in torch view**
- TorchViz3D receives `frames` and `activeTimestamp`.
- Workpiece switches from meshStandardMaterial to ShaderMaterial with uTemperatureMap.
- Thermal texture populated from interpolateThermalGrid(extractFivePointFromFrame(activeFrame)).
- Verification: Visual; hot region under torch, cold at edges.

**Criterion 2: 5–10°C color sensitivity**
- Define test: Two regions at 400°C vs 410°C must be visually distinguishable.
- Implement: Gradient with anchors every 5–10°C, or perceptual stretch in 350–500°C band.
- Verification: Side-by-side or A/B test with known temp diff.

**Criterion 3: No separate HeatmapPlate3D on replay**
- Replay page JSX: No <HeatmapPlate3D> when TorchViz3D has thermal.
- Verification: DOM/code review; only TorchViz3D in thermal slot.

**Criterion 4: Fallback when no thermal**
- When `frames` empty or `!showThermalMetal`: workpiece = flat gray plane.
- Verification: Session with no thermal_frames; visual = current TorchViz3D.

**Criterion 5: Canvas count**
- Replay: 2 TorchViz3D (with thermal) = 2 Canvases. No HeatmapPlate3D.
- Verification: Count Canvas instances; MAX_CANVAS_PER_PAGE still respected.

---

## 5. Scope Boundaries

### In Scope

1. **[ ]** Integrate thermal mesh into TorchViz3D workpiece when `frames` + `activeTimestamp` provided.
2. **[ ]** Remove HeatmapPlate3D from replay page.
3. **[ ]** Remove HeatmapPlate3D from demo expert column (or migrate to TorchViz3D-with-thermal).
4. **[ ]** Implement fine temperature gradient (5–10°C distinguishable) in shader or LUT.
5. **[ ]** Reuse thermal interpolation (5-point IDW) and frame resolution (getFrameAtTimestamp).
6. **[ ]** Fallback to flat workpiece when no thermal data.
7. **[ ]** (Optional) Temporal heat propagation — clarify in exploration.

### Out of Scope

1. **[ ]** Compare page thermal 3D — compare uses HeatMap; no TorchViz3D there.
2. **[ ]** Multiple thermal snapshot distances (e.g. layered plates) — use first/closest.
3. **[ ]** HeatmapPlate3D as standalone "heatmap-only" mode — deprecate for replay/demo.
4. **[ ]** Backend thermal accumulation model — use existing Frame data only unless specified.
5. **[ ]]** Redesign of demo novice thermal — may not have thermal_frames; defer.

### Scope Examples

1. **In scope:** TorchViz3D workpiece shows thermal when frames provided. **Out of scope:** HeatmapPlate3D remains as separate panel. **Why:** User explicitly wants unified view.
2. **In scope:** 5–10°C color sensitivity. **Out of scope:** 1°C resolution (overkill for display). **Why:** 5–10° meets "even 5–10 off is a lot."
3. **In scope:** Spatial thermal at current frame. **Out of scope:** Full physics-based temporal diffusion. **Why:** Clarify temporal in exploration; start with frame-accurate spatial.

---

## 6. Known Constraints & Context

### Technical Constraints

**Must use:**
- Three.js, R3F (existing).
- `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` patterns.
- snake_case, no raw data mutation.

**Must work with:**
- Thermal at 5 Hz; carry-forward or interpolation between frames.

**Cannot exceed:**
- MAX_CANVAS_PER_PAGE; WebGL context-loss handling.

**Performance:**
- 100×100 thermal mesh (or configurable); 60fps target.

### Design Constraints

- Temperature range: 0–500°C or 20–600°C (align with existing).
- Industrial/cyan theme.

---

## 7. Related Context

### Similar Features

**TorchViz3D** — Add thermal workpiece; reuse SceneContent pattern, OrbitControls.

**HeatmapPlate3D** — Source of thermal mesh logic; will be removed from replay/demo. Code to merge: Plate component, shaders, interpolation usage.

**heatmapData.ts** — Fine anchors for HeatMap; consider shared gradient constant or LUT for 3D.

### Related Issues/Plans

- `.cursor/issues/3d-warped-heatmap-plate.md` — Original HeatmapPlate3D issue; superseded by this unified approach.
- `.cursor/plans/unified-torch-heatmap-replay-plan.md` — May exist or be created.
- `documentation/WEBGL_CONTEXT_LOSS.md` — Canvas limits.

### Dependency Tree

```
Unified Torch + Thermal Metal
  ↑ Depends on: Frame, ThermalSnapshot, interpolateThermalGrid, TorchViz3D, R3F
  ↓ Replaces: HeatmapPlate3D on replay/demo
  Related: heatmapData gradient, HeatMap (fallback)
```

---

## 8. Open Questions & Ambiguities

**Question #1:** What exactly is "heat travel through the metal" — temporal accumulation, or just spatial spread at current frame?
- **Impact:** High — determines if we need thermal state model.
- **Assumption:** Start with spatial at current frame; explore temporal in Phase 2.
- **Who can answer:** User / product.

**Question #2:** Should we keep HeatmapPlate3D as optional toggle, or remove entirely?
- **Impact:** Medium — affects Canvas count, code surface.
- **Assumption:** Remove from replay/demo; deprecate component.
- **Who can answer:** Product.

**Question #3:** Gradient implementation: LUT texture vs. parametric shader vs. 50+ anchors?
- **Impact:** Medium — affects perf and flexibility.
- **Assumption:** Exploration will evaluate; LUT or parametric likely.
- **Who can answer:** Implementation.

**Question #4:** Workpiece size: 3×3 (current TorchViz3D) or 10×10 (HeatmapPlate3D)?
- **Impact:** Low — affects thermal detail visibility.
- **Assumption:** Match TorchViz3D scale; may need camera tweak.
- **Who can answer:** Design / exploration.

**Question #5:** Vertex displacement (warp) on metal — keep or flatten?
- **Impact:** Low — visual preference.
- **Assumption:** Keep warp for "thermal expansion" feel; configurable.
- **Who can answer:** User.

**Question #6:** Demo novice: does demo-data generate thermal_frames for novice? If not, novice keeps HeatMap.
- **Impact:** Low — demo layout.
- **Assumption:** Check demo-data; if novice has thermal, unify; else keep HeatMap.
- **Who can answer:** Code inspection (done: demo novice uses HeatMap, expert has HeatmapPlate3D).

**Question #7:** Temperature range: 0–500°C vs 20–600°C?
- **Impact:** Low — gradient bounds.
- **Assumption:** 0–500°C per user; or 20–500°C to match "ambient" heating.
- **Who can answer:** User.

**Question #8:** Interpolation between 5 Hz thermal frames for smoother playback?
- **Impact:** Medium — UX smoothness.
- **Assumption:** Use last-known (carry-forward) for now; linear interp as enhancement.
- **Who can answer:** Exploration.

**Question #9:** ESLint rule — update MAX_CANVAS or keep as-is?
- **Impact:** Low — fewer Canvases after merge.
- **Assumption:** No change needed; 2 TorchViz3D = 2 Canvases.
- **Who can answer:** Implementation.

**Question #10:** Compare page — any plan to add 3D thermal there?
- **Impact:** Low — out of scope.
- **Assumption:** No; compare stays HeatMap.
- **Who can answer:** Roadmap.

---

## 9. Initial Risk Assessment

**Risk #1: TorchViz3D complexity** — Adding thermal mesh increases component size and props.
- **Probability:** 60%. **Impact:** Medium.
- **Mitigation:** Extract ThermalWorkpiece subcomponent; keep TorchViz3D facade clean.

**Risk #2: Gradient tuning time** — 5–10°C sensitivity may require iteration.
- **Probability:** 50%. **Impact:** Medium.
- **Mitigation:** Prototype gradient options early; user feedback on sensitivity.

**Risk #3: Temporal propagation scope creep** — "Heat travel" could mean complex model.
- **Probability:** 40%. **Impact:** High.
- **Mitigation:** Phase 1 = spatial only; Phase 2 = temporal if validated.

**Risk #4: Workpiece scale mismatch** — 3×3 vs 10×10; thermal detail may be too small.
- **Probability:** 30%. **Impact:** Low.
- **Mitigation:** Use same grid density; scale plate to fit torch view; camera tuning.

**Risk #5: HeatmapPlate3D removal breaks compare** — Compare doesn't use it; low risk.
- **Probability:** 5%. **Impact:** Low.

**Risk #6: Shader LUT texture size** — 512×1 or 1024×1 for 0–500°C.
- **Probability:** 20%. **Impact:** Low.
- **Mitigation:** Standard approach; test on low-end GPU.

**Risk #7: Demo novice thermal** — If we add thermal to novice, need thermal_frames in demo-data.
- **Probability:** 25%. **Impact:** Low.
- **Mitigation:** Demo novice stays HeatMap unless thermal added to demo-data.

**Risk #8: Regression in TorchViz3D** — Existing torch/weld pool behavior.
- **Probability:** 25%. **Impact:** Medium.
- **Mitigation:** Thermal is additive; fallback preserves current behavior; tests.

**Top 3 Risks:** #1 (complexity), #2 (gradient), #3 (temporal scope).

---

## 10. Classification & Metadata

**Type:** feature

**Priority:** P1 (High)
- **Justification:** User explicitly requested; unifies UX; reduces Canvas count; improves thermal sensitivity. Aligns with industrial positioning. Not P0 (nothing broken) but high impact for replay/demo experience.

**Effort:** Large (16–24 hours)
- **Breakdown:** TorchViz3D thermal integration 6h, gradient redesign 4h, HeatmapPlate3D removal 2h, testing 4h, tuning/buffer 4–8h.
- **Confidence:** Medium — gradient and temporal scope may extend.

**Category:** Frontend

**Tags:** user-facing, high-impact

---

## 11. Strategic Context

**Product fit:** Industrial welding MVP; correctness, explainability. Unified thermal-torch view and fine sensitivity advance "industrial-grade" positioning.

**Capabilities unlocked:**
- Single coherent replay view.
- Fine thermal diagnosis (5–10°C visible).
- Reduced WebGL usage (fewer Canvases).

**User impact:** Replay and demo users see one view; thermal differences become actionable.

**Technical impact:** Consolidates HeatmapPlate3D into TorchViz3D; improves data utilization; reduces component count.

---

## Quality Metrics

| Metric | Minimum | Pass? |
|--------|---------|-------|
| Total words | 3,000 | ✅ |
| Pre-thinking | 500 | ✅ |
| Acceptance criteria | 12 | ✅ |
| Open questions | 10 | ✅ |
| Risks | 8 | ✅ |
| Similar features | 3 | ✅ |

---

## After Issue Creation

1. Resolve: "Heat travel" — temporal vs spatial.
2. Resolve: Gradient approach (LUT vs parametric).
3. Proceed to **Explore Feature** (technical exploration).
4. Create **Implementation Plan**.
