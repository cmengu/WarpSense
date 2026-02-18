
Implementation plan is done. Summary of what was produced:

## Plan Summary

**File:** `.cursor/issues/beautiful-pdf-report-plan.md`

### Phases (4 phases, 12 steps)

1. **Phase 1 — Dependencies and PDF Component (3h)**  
   - Install `@react-pdf/renderer` and `html-to-image`  
   - Create `WelderReportPDF.tsx` (dark theme, score, feedback, optional chart)  
   - Smoke test `renderToBuffer` in isolation  

2. **Phase 2 — API Route and Validation (4h)**  
   - Add `app/api/welder-report-pdf/route.ts` with POST handler  
   - Validate welder, score, feedback and return 400 when missing  
   - Use `renderToBuffer` and Node runtime  

3. **Phase 3 — Client Integration (5h)**  
   - Add `id="trend-chart"` wrapper (600×200px) around LineChart  
   - Add `lib/pdf-chart-capture.ts` using `html-to-image`  
   - Implement `handleDownloadPDF`: capture chart → POST → blob download  
   - Use loading and error state like supervisor export  

4. **Phase 4 — Tests (3h)**  
   - Mock `html-to-image` and assert fetch to `/api/welder-report-pdf` with correct payload  
   - Assert button is disabled during generation  
   - Keep Email Report alert test  

### Decisions Implemented

- **Option A:** `html-to-image` on client; base64 chart in POST body  
- **Chart fallback:** `chartDataUrl` null → chart section omitted  
- **API contract:** `POST /api/welder-report-pdf` with `{ welder, score, feedback, chartDataUrl? }`  
- **Filename:** `welder.name.replace(/[^a-zA-Z0-9_-]/g, '-')` for safe filenames  

### Risk Heatmap

- Main risks: `@react-pdf/renderer` with Next 16/React 19, and `html-to-image` on Recharts SVG  
- Mitigations: early smoke test, fallback when chart capture fails  

Total estimate: **~15h**, in line with the issue’s 12–16h.
