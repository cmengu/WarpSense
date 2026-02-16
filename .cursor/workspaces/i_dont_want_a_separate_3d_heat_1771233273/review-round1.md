
Here’s a concise summary of the Round 1 code review:

## Code review summary

The full report is in `.cursor/review-round1-output.md`. Summary:

### Findings

| Severity | Count | Highlights |
|----------|-------|------------|
| **CRITICAL** | 1 | WebGL resources (DataTexture, ShaderMaterial) created in `useMemo` in `ThermalPlate.tsx` — side effects in a pure memo, risks leaks and Strict Mode issues |
| **HIGH** | 6 | DataTexture update robustness, hardcoded comparison session ID, font loading, global test pollution, flat metal `planeGeometry` hardcoded to 3 |
| **MEDIUM** | 8 | Duplicate uniform updates, duplicate constants across files, repeated magic numbers, duplicate prop types |
| **LOW** | 6 | Hardcoded legend text, JSDoc clarity, comment correctness, color format usage |

### Critical fix

In `ThermalPlate.tsx`, move texture and material creation from `useMemo` into `useEffect`. `useMemo` is for pure computations; allocating and updating GPU-backed resources there breaks React’s expectations and can cause leaks in Strict Mode.

### What’s working well

- Clear separation of thermal extraction, interpolation, and rendering
- Context-loss handling with appropriate ARIA attributes
- Pure `temperatureToColor` with good edge-case handling
- Consistent use of `filterThermalFrames` and `extractCenterTemperatureWithCarryForward` in replay/demo
- Updated WebGL docs and ESLint rules

### Next steps

1. Fix the **CRITICAL** ThermalPlate `useMemo` usage (move resource creation to `useEffect`).
2. Address all **HIGH** issues.
3. Tackle **MEDIUM** items where practical.
4. Re-run the testing checklist, then request Round 2 review.
