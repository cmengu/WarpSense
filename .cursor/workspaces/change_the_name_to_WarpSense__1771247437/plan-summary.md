
```markdown
## Steps
1. File: my-app/src/constants/index.ts (or project constants barrel)
   - Action: Add theme export if barrel exists
   - Key code: `export * from './theme'` (or equivalent)

2. File: my-app/src/utils/heatmapData.ts
   - Action: Adjust tempToColorRange remap near line 118
   - Key code: `const t = 20 + p * (600 - 20)` → `const t = p * 500`

3. File: my-app/src/utils/heatmapData.ts (or thermal utils)
   - Action: Add NaN guard and optional test for deltaTempToColor
   - Key code: Guard with `Number.isNaN(d)`; test `expect(deltaTempToColor(NaN)).toBeDefined()`

4. File: my-app/src/data/mockData.ts
   - Action: Search for hardcoded hex colors
   - Key code: `rg '#10b981|#f59e0b' my-app/src/data/mockData.ts`

5. File: my-app/src/components/welding/TorchWithHeatmap3D.tsx
   - Action: Search for legacy Tailwind color classes
   - Key code: `rg 'cyan|green|amber' my-app/src/components/welding/TorchWithHeatmap3D.tsx`

## Critical Details
- Apply only these five fixes; no extra edits
- Keep `tempToColorRange` remap deterministic (no randomness)
- Use rg commands as-is for verification
```
