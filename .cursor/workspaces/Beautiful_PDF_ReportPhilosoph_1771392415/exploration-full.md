
Completed the technical exploration for the Beautiful PDF Report feature and wrote it to `.cursor/issues/beautiful-pdf-report-exploration.md`.

---

## Summary

- **Complexity:** Moderate — PDF layout is straightforward; chart capture via html-to-image adds some risk.
- **Approach:** Option A — `@react-pdf/renderer` + `html-to-image` (client chart capture), matching the spec.
- **Critical path:** New API route, PDF component, chart wrapper with `id="trend-chart"`, and download handler using the existing `downloadCSV` pattern.

### Codebase notes
- **`my-app/src/app/seagull/welder/[id]/page.tsx`** — All required data (`report`, `score`, `displayName`) is already in state.
- **`my-app/src/lib/export.ts`** — Same Blob → `createObjectURL` → download pattern applies; the PDF route will be the first API route in the app.
- **`my-app/src/components/charts/LineChart.tsx`** — Wrapper needs `id="trend-chart"` and fixed size (e.g. 600×200) for consistent html-to-image capture.

### Prototypes added
- **`my-app/prototype/pdf-chart-capture.ts`** — Chart capture helper using html-to-image.
- **`my-app/prototype/pdf-route.mts`** — Minimal `renderToBuffer` test for `@react-pdf/renderer`.

To run the PDF prototype:

```bash
cd my-app && npm install @react-pdf/renderer html-to-image
npx tsx prototype/pdf-route.mts
```

### Main risks
1. **html-to-image with Recharts** (Med/High) — Fallback: omit chart when capture fails.
2. **Compatibility with React 19 / Next 16** (Low/High) — Check in CI early.

### Effort
~11h total (Frontend 4h, Backend 3h, Testing 2h, Review 2h), 75% confidence.
