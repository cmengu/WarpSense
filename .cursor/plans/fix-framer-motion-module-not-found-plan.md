# Fix Framer Motion Module Not Found

**Overall Progress:** `0%`

## TLDR

Remove the obsolete `jest.mock('framer-motion')` from the landing page test. The landing page no longer uses framer-motion (replaced with CSS + useInView + useScrollParallax). The mock causes Jest to resolve a module that isn't installed, triggering "Module not found".

---

## Critical Decisions

- **Decision 1:** Remove the mock entirely — Landing page has zero framer-motion imports; mock is dead code.
- **Decision 2:** Do not add framer-motion to package.json — Migration to CSS/hooks is complete; no need to reintroduce the dependency.
- **Decision 3:** Run npm install after changes — Ensures package-lock.json is consistent if framer-motion was ever in lockfile.

---

## Tasks

### Phase 1 — Remove Obsolete Mock

**Goal:** Tests pass without resolving framer-motion; no "Module not found" error.

---

- [ ] 🟥 **Step 1: Remove jest.mock('framer-motion') from landing page test**

  **Context:** The landing page (`app/(marketing)/page.tsx`) uses custom CSS animations and `useInView` / `useScrollParallax` hooks. It does not import framer-motion. The test mocks framer-motion, which forces Jest to resolve the module. If framer-motion isn't in package.json, resolution fails.

  **Subtasks:**
  - [ ] 🟥 Open `my-app/src/__tests__/app/landing/page.test.tsx`
  - [ ] 🟥 Delete the entire `jest.mock('framer-motion', () => { ... });` block (lines 16–44)
  - [ ] 🟥 Update the file header comment to remove "Mocks framer-motion with Proxy-based mock"

  **✓ Verification Test:**

  **Action:**
  - Run `npm test -- --testPathPattern=landing` in `my-app/`

  **Expected Result:**
  - All landing page tests pass
  - No "Module not found: Can't resolve 'framer-motion'" error
  - No Jest resolution errors

  **How to Observe:**
  - **Terminal:** Test output shows "PASS" for landing page suite
  - **Console:** No module resolution errors in test output

  **Pass Criteria:**
  - Test suite exits with code 0
  - All landing tests (hero, stats, technology, feature cards, CTA, etc.) pass

  **Common Failures & Fixes:**
  - **If test fails with "motion is not defined":** Landing page or a child component still imports framer-motion — grep for `from 'framer-motion'` or `from 'motion'` and remove.
  - **If other tests fail:** Unrelated; the mock may have been affecting other suites — run full `npm test` to confirm scope.

---

- [ ] 🟥 **Step 2: Run npm install and verify build**

  **Context:** Ensures package-lock.json is clean; framer-motion should not appear if removed from package.json.

  **Subtasks:**
  - [ ] 🟥 Run `npm install` in `my-app/`
  - [ ] 🟥 Run `npm run build` to confirm no module resolution errors at build time

  **✓ Verification Test:**

  **Action:**
  - Run `npm install` then `npm run build` in `my-app/`

  **Expected Result:**
  - Build completes successfully
  - No "Module not found" for framer-motion or html-to-image (if that's a separate issue)

  **How to Observe:**
  - **Terminal:** Build output ends with "Compiled successfully" or equivalent
  - **node_modules:** `node_modules/framer-motion` should not exist (or is optional/transitive only)

  **Pass Criteria:**
  - Build succeeds
  - No framer-motion in direct dependencies

  **Common Failures & Fixes:**
  - **If build fails for other modules (e.g. html-to-image):** Separate issue; see `.cursor/issues/html-to-image-module-not-found.md`
  - **If framer-motion appears in lockfile:** Run `npm prune` or manually remove from lockfile if it's a stale transitive dep.

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Landing page has no framer-motion imports | `grep -r "framer-motion\|from 'motion'" my-app/src --include="*.tsx"` returns no matches in landing path | ⬜ |
| | Jest config loads | `npm test -- --listTests` includes landing test file | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟢 **10%** | Landing page secretly imports framer-motion via a shared component | Run tests after removing mock; if "motion is not defined" appears, grep for imports |
| Phase 2 | 🟢 **5%** | Build fails for unrelated reason (e.g. html-to-image) | Run build before and after; isolate framer-motion vs other module errors |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| Landing tests pass | `npm test -- landing` exits 0, all tests pass | **Test:** `npm test -- --testPathPattern=landing` → **Expect:** PASS, no module errors → **Location:** Terminal |
| Build succeeds | `npm run build` completes without module resolution errors | **Test:** `npm run build` → **Expect:** Compiled successfully → **Location:** Terminal |
| No framer-motion dependency | package.json and runtime do not require framer-motion | **Test:** Inspect package.json → **Expect:** No "framer-motion" in dependencies → **Location:** package.json |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
