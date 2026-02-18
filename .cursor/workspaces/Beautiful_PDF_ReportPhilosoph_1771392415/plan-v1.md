
The refined plan is written to `.cursor/issues/beautiful-pdf-report-plan.md`. Summary of the changes:

## Summary of Refinements

### Critical (Standard Critique + Adversarial)

1. **Step 4.5 — getApiBase**  
   - Clarified that Next.js inlines `NEXT_PUBLIC_*` at build.  
   - Tests adjusted for Node vs jsdom.  
   - Added Pre-Flight curl with basePath.

2. **Step 2.1 — Chunked encoding**  
   - Reject with 411 when `Transfer-Encoding: chunked` is present without `Content-Length`.  
   - Reduces OOM risk from chunked large bodies.

3. **Step 2.1 — `welder.name` validation**  
   - Added `toWelderName()` in route and component.  
   - Ensures string display; handles object/array by coercing to `"Unknown"`.

4. **Step 1.3 — Verification alignment**  
   - Dropped unexecutable “Large PNG (~130KB) PDF: OK” from pass criteria.  
   - Added `welder.name` object test to the prototype.

5. **Pre-Flight — Dev server**  
   - Added step to check server is running before curl (e.g. health check).

### Latent / Minor

6. **Step 4.6 — CI OOM risk**  
   - 413 test uses a ~5MB pad instead of 6MB.  
   - Documented 2GB minimum RAM.  
   - Optional: reduce `PAD_SIZE` or skip in CI.

7. **Step 2.3 — 413 verification**  
   - Uses `5*1024*1024 + 1024` (5MB+1KB) pad to exceed limit with lower memory use.

8. **Phase 1→2 boundary**  
   - Clarified that the prototype replaces the minimal Doc with `WelderReportPDF`.

### Additions

9. **Step 4.6 — New tests**  
   - 411 for chunked without `Content-Length`.  
   - `welder.name` object test (expect “Unknown”, no `[object Object]`).

10. **Step 3.3 — Manual smoke**  
    - Documented manual check: remove `id="trend-chart"`, click Download, confirm PDF without chart.

11. **Pre-Flight — Lockfile**  
    - Added “commit `package-lock.json`” and Pre-Flight check.

12. **Risk heatmap & Known Issues**  
    - Updated for chunked, `welder.name`, CI OOM, and `getApiBase` behavior.
