
Refinements are in place. Summary of what changed:

**Critical**

- **Step 2.1**: Invalid `Content-Length` (non-numeric or negative) now returns 400 before size checks.
- **Step 3.3**: Added `toWelderName(displayName)` before `sanitizeDownloadFilename` so filenames never show `[object Object]`.
- **Step 2.3**: Added `set -e` and explicit checks: `grep -q 'Unknown' /tmp/obj.pdf` and `! grep -q '\[object Object\]' /tmp/obj.pdf`.
- **Step 4.5**: Split tests into `api-base.node.test.ts` (Node) and `api-base.jsdom.test.ts` (jsdom) so the basePath path is actually run.
- **Step 4.6**: Added test for invalid `Content-Length` → 400; added `CI_LOW_MEM=1` to skip the 413 test in low-memory CI; fixed comment vs code mismatch.

**Other**

- **Step 1.2**: `sanitizeText` now strips zero-width and RTL-override characters.
- **Step 2.1**: Clarified route path as `src/app/api/...`.
- **Known issues**: Documented invalid `Content-Length` handling and 411 chunked test limitations.
- **Risk heatmap**: Updated getApiBase risk for jsdom test coverage.
