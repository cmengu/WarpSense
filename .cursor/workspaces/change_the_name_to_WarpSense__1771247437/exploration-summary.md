
Here’s the compressed version:

---

## Key Files

- `my-app/src/constants/theme.ts` (NEW) – thermal anchors, chart palette, semantic hex colors
- `my-app/src/utils/heatmapData.ts` – `TEMP_COLOR_ANCHORS` (blue→purple)
- `my-app/src/utils/heatmapShaderUtils.ts` – `ANCHOR_COLORS` (0–1 RGB, sync with heatmapData)
- `my-app/src/utils/deltaHeatmapData.ts` – delta scale: blue→white→purple
- `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` – 8 anchor colors on GPU
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` – weld pool color, lights
- `my-app/src/components/welding/HeatmapPlate3D.tsx`, `HeatMap.tsx`, `TorchAngleGraph.tsx` – cyan/green/amber → blue/purple
- `my-app/src/components/charts/PieChart.tsx`, `BarChart.tsx` – `CHART_PALETTE` / hex defaults
- Demo, landing, replay, compare, dashboard pages – branding + accents + error UI
- Deploy/docs: `deploy.sh`, `.env.example`, Dockerfiles, `CONTEXT.md`, `DEPLOY.md`
- Tests: demo, `heatmapData`, `HeatMap`, `heatmapShaderUtils`, `deltaHeatmapData`

## Architecture

- **Theme system:** `theme.ts` for hex (Recharts, Three.js, GLSL); Tailwind `blue-*`, `purple-*`, `violet-*` for layout
- **Thermal gradient:** 8 anchors, blue (cold) → purple (hot), 0–500°C; keep heatmapData, heatmapShaderUtils, GLSL aligned
- **Delta heatmap:** blue (B hotter) → white → purple (A hotter)
- **Semantic mapping:** Expert = blue-400, Novice = purple-400, Error = violet-600
- **HeatMap active column:** blue-500 outline; TorchAngleGraph target: purple-500

## Risks

- Thermal sources drift (heatmapData vs shader) → do changes in one PR; add sync test
- Missed colors (green/red/cyan) → grep color keywords and do visual QA
- Purple for errors less recognizable than red → strong violet, clear labels
- Brittle tests (hex checks) → update color assertions in same PR
