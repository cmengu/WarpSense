
Refined plan is done. Summary of changes from the critique and adversarial findings:

**Critical fixes**

1. **Step 2.3 – HTTP status assertions**  
   Each curl run now asserts the HTTP status (e.g. `test "$HTTP" = "400" || { echo "..."; exit 1; }`) for: missing score, score.total string, malformed JSON, oversized chartDataUrl, and 413. The script fails if any status is wrong.

2. **Step 2.1 – Content-Length limitation**  
   Known Issues now states that the server does not enforce a read limit on the body; a client can lie about `Content-Length`. Recommends a reverse-proxy body limit (nginx, Cloudflare) in production.

3. **Step 4.4 – Chart dimensions**  
   The test now asserts the style has `width: 600` and `height: 200` via `toMatch(/width.*600|600.*width/i)` and `toMatch(/height.*200|200.*height/i)`.

4. **toWelderName invariant**  
   - Component `toWelderName` updated to use `trim()` so whitespace-only names map to `"Unknown"` (aligned with API).
   - New invariant test in Step 4.6 for null, undefined, and array inputs to ensure the PDF/filename never contain `"[object Object]"` or `"undefined"`.

**Other updates**

- **Step 1.2**: File path for `sanitizeText` set to `WelderReportPDF.tsx`.
- **Step 1.1**: Verification uses `git status my-app/package-lock.json` for the lockfile.
- **Step 2.3**: Script skips the 413 test when `CI_LOW_MEM=1`.
- **Known Issues**:
  - CI env format and when 413 runs (nightly/staging).
  - Grep-based checks are heuristic; programmatic checks (e.g. pdf-parse) noted as optional.
- **Risk heatmap**: Added risk for client lying about Content-Length and for grep heuristic limits.
