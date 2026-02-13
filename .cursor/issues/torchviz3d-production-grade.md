# Production-Grade TorchViz3D Implementation

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `frontend` `3d` `ux` `stakeholder-demo`  
**Status:** Open

---

## TL;DR

Upgrade TorchViz3D from a basic proof-of-concept (cylinder + sphere) to an industrial-grade, photorealistic 3D visualization with PBR materials, OrbitControls, HDRI reflections, dynamic weld pool effects, and a professional HUD—so it impresses project managers and reflects the product vision during demos.

---

## Current State vs Expected Outcome

| Aspect | Current | Expected |
|--------|---------|----------|
| **Rendering** | Cylinder + sphere, `meshStandardMaterial` | Multi-part torch (handle, grip, nozzle, pool, halo), PBR, metalness 0.9, envMap |
| **Interactivity** | Static view | OrbitControls: drag rotate, scroll zoom (1–4 units), damping 0.05 |
| **Effects** | Discrete temp bands (blue/yellow/red) | Smooth gradient (blue→cyan→yellow→white), weld pool pulse, glow halo, contact shadows |
| **UI** | Label above canvas | Glass HUD (label + angle + temp), temperature scale indicator |
| **Demo page** | Minimal dev/torch-viz | Presets (Expert/Novice/Cold/Overheating), sliders, live simulation |

---

## Relevant Files

| File | Action |
|------|--------|
| `my-app/src/components/welding/TorchViz3D.tsx` | Replace with production implementation |
| `my-app/src/app/dev/torch-viz/page.tsx` | Replace with full demo (presets, sliders, simulation) |
| `my-app/src/app/replay/[sessionId]/page.tsx` | Verify integration (props unchanged) |
| `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Verify if TorchViz3D added for side-by-side |

---

## Risk & Notes

- **Bundle:** Drei + Three ~520KB gzipped. Acceptable for MVP.
- **SSR:** Use `dynamic(..., { ssr: false })` — already in place.
- **Data contract:** `angle` and `temp` props unchanged — no API changes.
- **HeatMap alignment:** Temp gradient must stay consistent with HeatMap semantics.

---

## How This Furthers Product Vision

- **Stakeholder confidence:** Reduces “it’s just a prototype” feedback.
- **Data integrity:** Same props, same replay flow — only visuals improve.
- **Exact replays:** Torch angle and weld pool color still driven by real frame data.
- **Demo-ready:** ~1.5 min script shows interactive 3D and side-by-side value.

---

## Full Spec

See `docs/ISSUE_TORCHVIZ3D_PRODUCTION_GRADE.md` for implementation checklist and detailed targets.
