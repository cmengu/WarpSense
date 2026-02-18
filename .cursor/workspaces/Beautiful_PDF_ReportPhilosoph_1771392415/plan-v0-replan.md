
Refined implementation plan is in `.cursor/issues/beautiful-pdf-report-plan.md`. Summary of changes:

## Critique and adversarial fixes applied

### Adversarial fixes
1. **Step 3.2 — Orphaned `toPng` promise**  
   Added `.catch(() => {})` on the `toPng` promise to avoid `unhandledrejection` when the timeout fires first.

2. **Step 2.1 — Request body size limit**  
   Reject requests with `Content-Length > 5MB` with 413. Reduces OOM risk from large bodies.

3. **Step 2.1 — `chartDataUrl` type coercion**  
   Use `typeof chartDataUrl === "string"` before length checks and only accept PNG (`startsWith("data:image/png")`).

4. **Step 1.2 — Non-PNG rejection**  
   Only render `Image` when `chartDataUrl` is a valid PNG data URL. Reject SVG/webp and other formats.

5. **Step 4.3 — `toPng` mock isolation**  
   Use `try/finally` to restore the default `toPng` mock after the chart fallback test.

### Critique fixes
6. **Pre-Flight — `npm ci`**  
   Use `npm ci` after install to avoid lockfile drift.

7. **Step 3.3 — basePath handling**  
   Moved `getApiBase` into `lib/api-base.ts` and added unit tests (Step 4.5).

8. **Step 4.4 — Trend-chart assertion**  
   Added a test that checks the `trend-chart` element exists with `data-testid`.

9. **Step 2.2 — JSON parsing**  
   Use `jq` where available for response parsing.

10. **Step 2.3 — Oversized tests**  
   Use `node -e` to generate large payloads instead of shell brace expansion to reduce OOM risk on CI.

### Other updates
- **Step 4.6** — API tests now include the 413 body-size case.
- **Step 4.5** — New tests for `getApiBase()`.
- **Risk heatmap** — Updated with adversarial risks and mitigations.
- **Known issues** — Documented Content-Length caveats and `getApiBase` usage.

Total steps: 16 across 4 phases (est. ~17.5h).
