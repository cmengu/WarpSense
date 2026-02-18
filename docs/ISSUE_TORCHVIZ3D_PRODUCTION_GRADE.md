# Issue: Production-Grade TorchViz3D Implementation

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `frontend` `3d` `ux` `stakeholder-demo`

---

## TL;DR

Upgrade TorchViz3D from a basic proof-of-concept (cylinder + sphere) to an industrial-grade, photorealistic 3D visualization with PBR materials, OrbitControls, HDRI reflections, dynamic weld pool effects, and a professional HUD—so it impresses project managers and reflects the product vision during demos.

---

## Current State vs Expected Outcome

### Current State
- Basic cylinder (handle) + sphere (weld pool) with simple `meshStandardMaterial`
- Static view, no camera interaction
- 3 lights (ambient + directional + point), no environment reflections
- Discrete temp color bands: blue (<310°C), yellow (310–455°C), red (>455°C)—no smooth gradient
- Simple label above canvas; no real-time stats overlay
- No weld pool pulse, no glow halo, no contact shadows
- Used on replay page and compare page; minimal dev/torch-viz demo

### Expected Outcome
| Feature | Target |
|---------|--------|
| **Rendering** | Multi-part torch assembly (handle, grip, nozzle cone, weld pool, glow halo) with PBR materials, metalness 0.9, envMap reflections |
| **Interactivity** | OrbitControls: drag to rotate, scroll to zoom (1–4 units), constrained polar angle, damping 0.05 |
| **Effects** | Pulsing weld pool (2% scale), temp-based glow intensity (0.5–3.0), smooth temp gradient (blue→cyan→yellow→white), contact shadows, HDRI warehouse preset |
| **UI** | Glass-morphism HUD (label + live angle + temp), temperature scale indicator (bottom-right gradient bar) |
| **Demo Page** | Presets (Expert/Novice/Cold Start/Overheating), sliders, live simulation with ±3° / ±20°C variation, quality score display |

---

## Relevant Files

| File | Action |
|------|--------|
| `my-app/src/components/welding/TorchViz3D.tsx` | Replace with production implementation |
| `my-app/src/app/dev/torch-viz/page.tsx` | Replace with full demo (presets, sliders, simulation, industrial theme) |
| `my-app/src/app/replay/[sessionId]/page.tsx` | Verify integration (already uses TorchViz3D; props unchanged) |
| `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Verify side-by-side usage if TorchViz3D is added there |

---

## Risk & Notes

- **Bundle size:** Drei + Three add ~520KB gzipped. Acceptable for MVP.
- **SSR:** Must use `dynamic(..., { ssr: false })` for WebGL. Already in place.
- **Data contract:** `angle` and `temp` props stay the same—no API changes.
- **HeatMap alignment:** Temperature gradient (blue→yellow→white-hot) should remain conceptually aligned with existing HeatMap semantics for consistency.
- **Performance:** Target 60fps. If issues arise: reduce shadow map (2048→1024), simplify geometry (32→24 segments).

---

## Implementation Checklist

- [ ] Add `@react-three/drei` dependencies (OrbitControls, Environment, ContactShadows, PerspectiveCamera)
- [ ] Implement multi-layer torch assembly (handle, grip, nozzle, weld pool, glow halo)
- [ ] Add temperature color algorithm with smooth gradient (blue→cyan→yellow→white)
- [ ] Wire useFrame for smooth rotation lerp and weld pool pulse
- [ ] Add OrbitControls (enablePan: false, minDistance: 1, maxDistance: 4)
- [ ] Add 5-light rig + HDRI warehouse + ContactShadows
- [ ] Add HUD overlay (label, angle, temp) and temperature scale indicator
- [ ] Configure Canvas GL (ACESFilmicToneMapping, powerPreference: high-performance)
- [ ] Update dev/torch-viz page with presets, sliders, live simulation, industrial theme
- [ ] Run verification: replay page + compare page (if applicable)

---

## How This Furthers the Product Vision

- **Stakeholder confidence:** Reduces “it’s just a prototype” feedback; visualization reads as production-ready.
- **Data integrity:** Same props (`angle`, `temp`), same replay/compare data flow—only visual presentation improves.
- **Exact replays:** Torch angle and weld pool color still driven by real frame data; no guessing.
- **Demo-ready:** Project manager script (~1.5 min) demonstrates interactive 3D, live simulation, and side-by-side comparison value.

---

## Reference

- Implementation guide: .cursor/context/torchviz3d-five-steps-context.md (or equivalent)
- Current TorchViz3D: `my-app/src/components/welding/TorchViz3D.tsx` (137 lines)
- Dev demo: `my-app/src/app/dev/torch-viz/page.tsx`
