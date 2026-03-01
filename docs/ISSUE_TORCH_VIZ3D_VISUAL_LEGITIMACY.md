# Issue: TorchViz3D — Visual Legitimacy Plan

**Type:** Improvement  
**Priority:** Normal  
**Effort:** ~3–4 hours total (Phase 1: 1–2h, Phase 2: 1h, Phase 3: 30 min)  
**Labels:** `frontend` `3d` `ux` `torch-viz`

---

## TL;DR

Upgrade the 3D torch visualization from generic (stacked cylinders, flat lighting, uniform surfaces) to industrial-legitimate: realistic MIG gun geometry (gooseneck, nozzle, contact tip), PBR lighting that produces specular streaks, material variation (rubber, brass, copper, gunmetal), and HUD/color alignment with thermal heatmap (green→amber→red).

---

## Current State vs Expected Outcome

**Current State**
- Torch: straight cone + cylinder + oversized arc ball (radius 0.12)
- Symmetric soft lighting — all surfaces read similarly
- Uniform roughness across materials
- `getWeldPoolColor` already green/orange/red — but HUD and gradient bar still blue theme
- Single cone for nozzle, no contact tip, no grip bands, no trigger housing

**Expected Outcome**
- Gooseneck with progressive rotations simulating real MIG bend
- Two-part nozzle (body + chamfered tip) + copper contact tip (radius 0.0065)
- Arc point radius 0.018 (pinpoint), glow halo 0.055
- 4 grip bands, trigger housing, cable collar, workpiece seam + target ring
- RectAreaLight + hardened key light + dim fill + warm under-light from arc
- Material variation: rubber (0.98 roughness), brass nozzle (0.35), copper tip (0.18)
- HUD: slate tones, temp readout color by temp, gradient bar green→amber→red

---

## Dependency

**Blocked by:** WeldTrail work completing on current branch first. Geometry reference output exists and is ready to apply after that.

---

## TorchWithHeatmap3D — Mandatory Refactor

TorchWithHeatmap3D does **not** import or embed TorchViz3D. It duplicates the torch assembly in its own SceneContent. Replay, demo, and compare pages use TorchWithHeatmap3D — these are the investor-facing pages.

**Why you cannot "compose TorchViz3D":** TorchViz3D is a full component with its own Canvas, HUD overlay, context-loss handler, footer, and temp scale bar. R3F does not allow nested Canvas components; attempting it yields two WebGL contexts and immediate breakage. Do not try to nest or embed TorchViz3D inside TorchWithHeatmap3D.

**Correct approach:** Extract the torch geometry group (the part inside SceneContent that renders the torch meshes, lights, and weld pool) into a separately exported component — **`TorchSceneContent`**. Have both TorchViz3D and TorchWithHeatmap3D import and render it inside their own respective Canvases. Single source of truth for geometry, materials, and lighting.

**Only acceptable temporary stopgap:** If extraction is blocked, applying the same changes to both files is allowed **only** if a follow-up ticket is filed immediately to extract TorchSceneContent. Duplication without follow-up re-introduces tech debt.

---

## Phase 1 — Lighting (~1–2h)

- **RectAreaLight:** Position `[0, 3, -1]`, size `4×0.4`, simulates overhead shop fluorescent. **Call `RectAreaLightUniformsLib.init()` once** — at module level, but guard with `if (typeof window !== 'undefined')` to avoid SSR errors (Next.js can run module-level Three.js code during SSR even with `'use client'`). Alternatively, lazy-init inside Canvas `onCreated` the first time. Do not put it in useEffect — SceneContent remounts on WebGL context loss recovery; init is idempotent but useEffect is the wrong place.
- **Harden key light:** Position `[4, 8, 3]`, intensity `2.2` (from `1.8`)
- **Dim fill:** Intensity `0.15` (from `0.4`)
- **Arc under-light:** Point light at `[0, -0.25, 0.1]`, intensity `0.3`. **Color must be reactive** — driven by the same `getArcColor(temp)` call that feeds the arc sphere. Do not hardcode; it updates as temp changes during replay.

---

## Phase 2 — Surface Variation (~1h)

- Grip bands: `roughness: 0.98`, `metalness: 0.0`
- Handle barrel: upper section `roughness: 0.28` (wear away from nozzle)
- Nozzle: `roughness: 0.35` (brass oxidizes)
- Contact tip: `roughness: 0.18` (threaded, not polished)
- Arc emissiveIntensity: clamp max at `4.0` (avoid bloom)

---

## Phase 3 — Environment (~30 min)

- **Default:** `preset="city"` — harder, more directional reflections than warehouse
- **Only pursue custom HDR** (`/public/hdri/shipyard.hdr`) if city produces obviously wrong reflections on the nozzle. Do not cycle through options arbitrarily.

---

## Files to Touch

| File | Change |
|------|--------|
| `TorchViz3D.tsx` | Apply geometry + color reference, Phase 1–3. After lighting verified, extract torch+lights into TorchSceneContent and import it. |
| `TorchSceneContent.tsx` | **Create** — exported component containing torch geometry group + lights. Props: `angle`, `temp`. RectAreaLightUniformsLib.init() at module level here (not TorchViz3D — replay page loads TorchWithHeatmap3D only). Import `@/constants/welding3d` for all Y positions; no hardcoded values. Both TorchViz3D and TorchWithHeatmap3D import and render it. |
| `TorchWithHeatmap3D.tsx` | Replace duplicated torch assembly with `<TorchSceneContent angle={angle} temp={temp} />`. (Stopgap: apply same changes + file follow-up ticket) |
| `heatmapShaders.test.ts` | **Verify before closing ticket** that no assertions use old blue hex values from `getWeldPoolColor`. If they do, update to green/amber/red. Do not assume "no changes required" — confirm. |

---

## Build Order

1. Wait for WeldTrail branch to complete
2. Apply geometry + color reference to TorchViz3D
3. **Phase 1 — lighting** (do before refactor; lighting reveals whether surface work is needed). Verify on `/dev/torch-viz` that torch reads as polished metal.
4. **Extract TorchSceneContent** and refactor TorchWithHeatmap3D to import it. Do not extract before lighting — otherwise replay page shows new geometry with old flat lighting and appears broken.
5. Verify against checklist (including replay page)
6. Phase 2 — surface variation if still needed
7. Phase 3 — environment (`preset="city"`)
8. Run tests and verify heatmapShaders assertions

---

## Verification Checklist

- [ ] Gooseneck reads as bent neck from default camera
- [ ] Contact tip visible, eye lands on it naturally
- [ ] Arc at high temp reads as pinpoint, not ball
- [ ] Barrel has visible specular streak from rect light
- [ ] Shadow side of gun goes dark
- [ ] Temp readout in HUD changes color with temp
- [ ] Gradient bar reads green → amber → red
- [ ] **Open replay page** (`/replay/[sessionId]`), confirm gooseneck geometry and green→amber→red arc color visible — investor-facing path uses TorchWithHeatmap3D
- [ ] `heatmapShaders.test.ts` passes (after verifying no blue hex assertions)
- [ ] WebGL context loss flow unchanged

---

## Risk / Notes

- **RectAreaLightUniformsLib:** Init must live in TorchSceneContent (not TorchViz3D). Replay page loads TorchWithHeatmap3D without TorchViz3D; init in TorchViz3D would never run. Module level with `if (typeof window !== 'undefined')` to avoid SSR.
- **welding3d constants:** TorchSceneContent must import and use `@/constants/welding3d` (TORCH_GROUP_Y, WELD_POOL_OFFSET_Y, etc.) for all Y positions. Hardcoded Y values silently misalign with TorchWithHeatmap3D workpiece.
- **TorchWithHeatmap3D:** Replay/demo/compare use it. Checklist must include a replay-page visual check or the investor path can ship with stale geometry.
- **WebGL:** No new Canvas; stays within context limit.

---

## Vision Alignment

From `vision.md`:

- *"The story told visually — expert vs novice comparison that makes the value self-evident"* — A legitimate-looking torch increases credibility of the thermal and angle data.
- *"Technical credibility"* — Polished PBR lighting and geometry signal a production system, not a prototype.
- *"Something they can forward"* — Screenshots of replay with a realistic torch travel better in investor conversations.
