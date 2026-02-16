
A full issue already exists at `.cursor/issues/metal-heatmap-y-position-clipping-torch.md`. Here’s a concise summary:

---

## Issue status: **complete**

### Root cause

The metal heatmap (ThermalPlate) clips through the torch because:

| Element | Y position | Notes |
|--------|------------|--------|
| Workpiece base | -0.6 | `group position={[0, -0.6, 0]}` |
| Max vertex displacement | +0.5 | `uMaxDisplacement` in ThermalPlate |
| **Metal surface max Y** | **-0.1** | -0.6 + 0.5 |
| Weld pool center | -0.2 | Torch group 0.4 + sphere -0.6 |

So the metal surface can reach Y = -0.1 while the weld pool center is at Y = -0.2, so the metal rises above the weld pool and clips into the torch.

### Proposed fix

1. **Lower workpiece base** from Y = -0.6 to around Y = -0.85 to -0.9.
2. **Align scene elements** (angle ring, grid, ContactShadows) with the new metal plane.
3. **Optionally** reduce `uMaxDisplacement` from 0.5 to ~0.25–0.35.

Example: workpiece Y = -0.85 → metal max Y = -0.85 + 0.5 = -0.35, below weld pool at -0.2.

### Files affected

- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` (positions around lines 189, 212, 222, 225)
- Optionally: `my-app/src/components/welding/ThermalPlate.tsx` (`uMaxDisplacement`)

### Issue metadata

- **Type:** Bug  
- **Priority:** P2 (Normal)  
- **Effort:** 4–8 hours  
- **Tags:** user-facing, quick-win, high-impact, low-effort  

### Next steps

1. Decide: lower metal vs. reduce displacement vs. both.
2. Choose a gap: ~0.1–0.2 units between metal max surface and weld pool.
3. Proceed to Phase 2 (Explore) or implement directly (the fix is well-scoped).

---

Because you mentioned “several bugs” and “first off,” should I start creating issues for the other bugs as well? If so, share the next one and I’ll follow the same template.
