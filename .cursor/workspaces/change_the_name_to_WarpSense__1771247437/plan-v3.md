
Applied all five refinements from the critique and regression analysis:

1. **Step 1.3 code block** — Added the full import and `ANCHOR_COLORS` alias plus a note to remove the local definition.

2. **Step 4.7 build verification** — Added `npm run build` before `npm test`, with a note that deploy pipelines typically run the build.

3. **Rollback procedure** — Added a new section before Pre-Flight with steps: `git revert <PR-commit>`, `npm test`, then redeploy if needed.

4. **Step 2.3 mockData note** — Added a note to confirm line numbers via `rg '#10b981|#f59e0b' my-app/src/data/mockData.ts` when mockData structure changes.

5. **Step 1.5 NaN handling** — Updated Common failures to mention an optional `expect(tempToColor(NaN)).toBeDefined()` and added an optional edge-case test block.

Success Criterion #15 was updated to require both `npm run build` and `npm test`.
