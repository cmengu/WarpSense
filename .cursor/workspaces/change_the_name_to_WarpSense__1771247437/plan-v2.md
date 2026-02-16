
The plan at `.cursor/plans/warpsense-rebrand-blue-purple-plan.md` is updated with all six critique refinements:

1. **Step 1.7 heatmapShaderUtils 0°C** — 0°C test updated for `THERMAL_ANCHOR_COLORS_0_1[0]`: `expect(r).toBeCloseTo(0.12, 2)`, `expect(g).toBeCloseTo(0.23, 2)`, `expect(b).toBeGreaterThan(0.5)`.

2. **Step 1.7 heatmapData expert/novice** — Expert/novice tests switched from yellow-ish/red-ish to purple-ish: `expect(rgb.b).toBeGreaterThan(rgb.r)` and `expect(rgb.r).toBeGreaterThan(100)` for both ~490°C and ~520°C.

3. **Step 1.7 clamp test** — Explicitly renamed "clamps temps below 20 to 20" → "clamps temps below 0 to 0" with matching assertions for the [0,500] range.

4. **Step 4.5 grep** — Simplified to `rg 'green|red|cyan|amber|yellow|orange|pink|emerald|teal|lime' my-app/src --glob '!*.test.*' --glob '!*.spec.*'`.

5. **Step 2.3 mockData** — Specified line 79 (`color: '#10b981'` → `'#2563eb'`) and line 118 (`color: '#f59e0b'` → `'#6366f1'`), plus a grep verification step.

6. **Step 1.5 thermal sync** — Added explicit rgb-to-hex conversion helpers: `toHex` and `rgbToHex(r,g,b)`.
