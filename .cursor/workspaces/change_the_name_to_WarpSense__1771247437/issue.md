
Created an issue document at `.cursor/issues/warpsense-rebrand-blue-purple-palette.md` using the full Create Issue (Deep Capture Mode) template. Summary:

## Summary for You

### Title
**[Improvement] WarpSense Rebrand — Name Change and Blue/Purple-Only Dark Color Palette**

### Scope (In Scope)

**Name → WarpSense**
- Demo header: "Shipyard Welding — Live Quality Analysis" → "WarpSense — Live Quality Analysis"
- Layout metadata: "Live Demo — Shipyard Welding" → "Live Demo — WarpSense"
- `deploy.sh`, `.env.example`, Dockerfiles, CONTEXT.md, DEPLOY.md

**Colors → Blue & Purple Only**
- **Landing page:** Replace green, orange, pink, emerald gradients with dark blue/purple gradients
- **Demo page:** Expert (green) / Novice (red) → two blue/purple shades (e.g., blue vs purple)
- **Thermal heatmaps:** Blue→red → blue→purple (cold→hot)
- **3D components:** Cyan, green, amber → blue/purple
- **Charts:** PieChart, BarChart, mockData → blue/purple palette
- **Error/danger:** Red → purple/violet
- **HeatMap, TorchAngleGraph, AppNav:** Replace green/cyan with blue/purple

**Out of Scope**
- Docker container renames (`shipyard_*` → `warpsense_*`) to avoid breaking existing deploys

### Files to Touch (~25)
- `demo/page.tsx`, `demo/layout.tsx`, `(marketing)/page.tsx`
- `heatmapData.ts`, `heatmapShaderUtils.ts`, `heatmapFragment.glsl.ts`
- `TorchWithHeatmap3D`, `TorchViz3D`, `HeatmapPlate3D`
- `HeatMap`, `TorchAngleGraph`, `PieChart`, `BarChart`
- Error panels in demo, replay, compare, dashboard
- Deploy scripts and docs
- Tests (demo, heatmapData, HeatMap)

### Open Questions for You
1. **Palette:** Confirm using Tailwind dark blues (blue-800/900/950) and purples (purple-800/900/950), or specify hex values.
2. **Thermal gradient:** OK to change cold→hot from blue→red to blue→purple?
3. **Expert vs Novice:** Prefer blue vs purple, or two different blues?

### Effort
Estimated **12–20 hours**, Medium priority (P2).

The issue is ready for **Phase 2: Explore Feature** (technical exploration) and then **Phase 3: Create Plan** (step-by-step implementation).
