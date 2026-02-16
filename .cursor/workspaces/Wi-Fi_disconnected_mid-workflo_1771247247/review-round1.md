
Round 1 of the code review for the metal heatmap Y-position clipping fix is done. Summary:

---

## Code Review Report - Round 1 Summary

**Files reviewed:** 5 (1 created, 4 modified)  
**Total issues:** 20 (CRITICAL: 0, HIGH: 2, MEDIUM: 6, LOW: 12)

---

### HIGH priority (fix before deploy)

1. **`TorchWithHeatmap3D.tsx:153`** — Torch group uses hardcoded `0.4` instead of `TORCH_GROUP_Y` from `welding3d.ts`. Breaks single source of truth and could reintroduce clipping if constants change.

2. **`ThermalPlate.tsx:82`** — `uMaxDisplacement` is hardcoded `0.5` instead of importing `MAX_THERMAL_DISPLACEMENT` from `welding3d.ts`. Risk of drift and incorrect thermal displacement.

---

### MEDIUM priority (should fix soon)

- Redundant `frames?.` optional chaining on line 269
- `plateSize` not validated in ThermalPlate (can be 0 or negative)
- Add `useEffect` coupling comment in ThermalPlate
- Add `WELD_POOL_CENTER_Y` derivation test in `welding3d.test.ts`
- Type `thermalFrame` as `Frame` in the test
- Extract magic number `0.01` for `ANGLE_RING_Y` / `CONTACT_SHADOWS_Y`

---

### LOW priority (nice to have)

- Extract magic numbers in glow formula, camera position, point light position
- Add `aria-label` on temp scale bar
- Document no `receiveShadow` on ThermalPlate
- Minor JSDoc and test cleanups

---

### What’s working well

- No `any`, `console.log`, or `@ts-ignore`
- Clear central constants in `welding3d.ts`
- Solid constraint tests in `welding3d.test.ts`
- Proper WebGL listener cleanup in TorchWithHeatmap3D
- Context-loss overlay has appropriate accessibility attributes
- Correct use of `getFrameAtTimestamp` and `extractFivePointFromFrame`

---

Full report path: `.cursor/review-round1-metal-heatmap-clipping-output.md`

Next step: fix the two HIGH issues (use `TORCH_GROUP_Y` and `MAX_THERMAL_DISPLACEMENT`), then request Round 2 review.
