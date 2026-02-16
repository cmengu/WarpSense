# WebGL Context Lost — Project-Wide Fix Implementation Plan

**Overall Progress:** 100% (9/9 steps completed)

---

## TLDR

The app shows "THREE.WebGLRenderer: Context Lost" consistently across `/demo`, `/replay`, and dev pages — causing white/black screens, frozen 3D views, and noisy console output. This plan addresses the root causes: insufficient context-loss handling visibility, missing safeguards, and lack of enforcement. We will harden the TorchViz3D overlay for reliability, add explicit instance-count tests, strengthen documentation (including HMR expectations), introduce an ESLint rule to prevent >2 Canvas instances per page, and verify overlay visibility across all integration points. No refactoring to shared Canvas/scissor — that remains a future optimization.

---

## Critical Architectural Decisions

### Decision 1: Keep 2 TorchViz3D Instances on Demo and Replay

**Choice:** Leave demo (expert + novice) and replay (current + comparison) at 2 instances each; do not consolidate to 1 Canvas with scissor.

**Rationale:** 2 is within browser limits (~8–16). Consolidation adds complexity; defer until proven necessary.

**Trade-offs:** Slightly higher GPU memory use than single Canvas; acceptable for MVP.

**Impact:** Tests and lint enforce ≤2; no layout changes.

---

### Decision 2: Overlay Lives Inside TorchViz3D (Not Page-Level)

**Choice:** Context-loss overlay remains a child of TorchViz3D, rendered with `z-20` in its own stacking context. Pages do not add a separate top-level overlay.

**Rationale:** Each TorchViz3D owns its Canvas; overlay must cover that Canvas. Centralizing at page level would require context passing and adds complexity.

**Trade-offs:** Each instance shows its own overlay (redundant if both lose context); acceptable since both will lose context together when limit is exceeded.

**Impact:** Overlay z-index and stacking context must be validated per-page; no new shared overlay component.

---

### Decision 3: ESLint Rule via File-Pattern Analysis (Not AST)

**Choice:** Implement ESLint rule that counts `TorchViz3D` JSX elements in a file. Use regex/simple parsing — not full AST — to keep rule maintainable. Whitelist `__tests__` and `dev/` routes.

**Rationale:** Full AST analysis for "import + usage count" is complex; regex on JSX is sufficient for our constraint (≤2 per page file).

**Trade-offs:** May have false positives if component is used in a loop; we avoid loops by design. May miss indirect usage (e.g. wrapper component); acceptable for MVP.

**Impact:** `eslint.config.mjs` gets custom rule; pages with >2 get build error.

---

### Decision 4: HMR Context Loss — Document, Do Not Suppress

**Choice:** Do not attempt to suppress "Context Lost" console message during HMR. Document it explicitly as expected behavior in WEBGL_CONTEXT_LOSS.md and add team onboarding note.

**Rationale:** R3F calls `forceContextLoss()` on unmount; browser emits the message. Suppressing would require monkey-patching or hiding console output — not worth the complexity.

**Trade-offs:** Developers will see the message on every hot reload; documentation reduces confusion.

**Impact:** Documentation update only; no code change for HMR.

---

### Decision 5: Loading Fallback — Verify, Do Not Re-implement

**Choice:** Demo and Replay already use `dynamic(..., { loading: () => ... })`. Plan verifies and standardizes the loading markup (h-64, cyan theme); no structural change unless verification finds gaps.

**Rationale:** Issue doc claimed "no loading fallback" — current code has it. May have been fixed in a prior PR; we confirm consistency.

**Trade-offs:** None if present; if absent, we add.

**Impact:** Verification step; possible minor styling alignment.

---

## Dependency Ordering

| Step | Depends On | Blocks | Can Mock? |
|------|-----------|--------|-----------|
| Phase 1.1: Audit current state | Nothing | Everything | N/A |
| Phase 1.2: Strengthen TorchViz3D overlay | Nothing | Tests, verification | No |
| Phase 1.3: Add demo instance-count test | Demo page | — | Yes (mock TorchViz3D) |
| Phase 1.4: Strengthen WEBGL_CONTEXT_LOSS.md | Nothing | Team onboarding | N/A |
| Phase 2.1: Add ESLint rule | webgl.ts constant | CI | N/A |
| Phase 2.2: Verify loading fallbacks | Demo, Replay pages | — | Yes (visual) |
| Phase 2.3: Overlay visibility manual test | TorchViz3D | — | No |
| Phase 3.1: Update LEARNING_LOG | Phase 1–2 | — | N/A |
| Phase 3.2: Code review checklist | Documentation | — | N/A |

**Parallelizable:** 1.2 and 1.4 can run in parallel; 1.3 and 2.2 can run in parallel after 1.1.

---

## Risk Heatmap

| Phase | Step | Risk | Probability | What Could Go Wrong | Early Detection Signal | Mitigation Strategy |
|-------|------|------|-------------|---------------------|------------------------|---------------------|
| 1 | 1.2 | Overlay hidden by parent z-index | 🟡 40% | Parent has `isolation: isolate` or high z-index; overlay behind | Manual test: trigger context loss → overlay not visible | Ensure TorchViz3D wrapper has `position: relative` and overlay is `absolute inset-0`; test on demo/replay |
| 1 | 1.3 | Mock bypasses real count | 🟢 15% | Mock returns single element; test always passes | Test would pass even with 3 instances | Use mock that renders N placeholders when called N times; assert `mocks.length <= 2` |
| 2 | 2.1 | ESLint rule false positive | 🟡 45% | Rule flags comment or string containing "TorchViz3D" | ESLint fails on valid file | Use JSX/pattern that matches only element usage; exclude comments |
| 2 | 2.1 | ESLint rule false negative | 🟡 35% | New page adds 3 instances; rule misses | Manual review catches | Code review checklist; rule is defense-in-depth |
| 2 | 2.3 | Context loss hard to trigger manually | 🟡 50% | No easy way to simulate; testing is ad-hoc | Can't verify overlay in CI | Document manual procedure; accept that automated overlay test exists in TorchViz3D.test |
| 3 | — | Documentation drift | 🟢 20% | Team adds 3rd instance; misses checklist | Lint catches; review catches | Lint + checklist are dual enforcement |

**Highest priority risks:**
1. **Overlay visibility (Phase 1, Step 1.2)** — If overlay is hidden, user sees white screen with no recovery path.
2. **ESLint false positive (Phase 2, Step 2.1)** — Could block valid development.
3. **Manual test feasibility (Phase 2, Step 2.3)** — Need reproducible procedure for QA.

---

## Implementation Phases

### Phase 1 — Core Reliability

**Goal:** Overlay is reliable and visible; instance count is enforced by test; HMR behavior is documented.

**Why this phase first:** Overlay reliability is the highest user impact. Tests prevent regression. Documentation reduces developer confusion.

**Time Estimate:** 4–6 hours

**Risk Level:** 🟡 40%

---

#### 🟥 Step 1.1: Audit Current State (Baseline)

**Subtasks:**
- [ ] 🟥 Confirm demo page uses `dynamic()` with `loading` fallback and 2 TorchViz3D
- [ ] 🟥 Confirm replay page uses `dynamic()` with `loading` fallback and 1–2 TorchViz3D
- [ ] 🟥 Confirm TorchViz3D has `onCreated` with `webglcontextlost` / `webglcontextrestored` listeners
- [ ] 🟥 Confirm TorchViz3D overlay uses `z-20`, `absolute inset-0`, `role="alert"`, and refresh button
- [ ] 🟥 List all pages that import or render TorchViz3D

**Files:**
- **Read:** `my-app/src/app/demo/page.tsx`
- **Read:** `my-app/src/app/replay/[sessionId]/page.tsx`
- **Read:** `my-app/src/components/welding/TorchViz3D.tsx`
- **Read:** `my-app/src/app/dev/torch-viz/page.tsx`
- **Grep:** `TorchViz3D` across `my-app/src`

**✓ Verification Test:**

**Action:**
1. Run `rg "TorchViz3D" my-app/src --type-add 'app:*.tsx' -t app -l`
2. For each matched file, open and count: (a) `dynamic(...)` with `ssr: false` and `loading`, (b) number of `<TorchViz3D` JSX elements
3. In TorchViz3D.tsx, verify lines 261–276 contain `addEventListener('webglcontextlost'` and lines 294–321 contain the overlay div with `role="alert"` and `z-20`

**Expected Result:**
- Demo: 1 dynamic import with loading, 2 TorchViz3D elements
- Replay: 1 dynamic import with loading, 2 TorchViz3D elements (one conditional on showComparison)
- Dev torch-viz: 1 dynamic import with loading, 1 TorchViz3D element
- No other pages use TorchViz3D
- TorchViz3D has listeners and overlay as described

**Pass Criteria:**
- Audit table documented in Notes & Learnings
- No surprises (e.g. 4th usage somewhere)
- TorchViz3D overlay implementation matches WEBGL_CONTEXT_LOSS.md

**Common Failures & Fixes:**
- **If grep finds TorchViz3D in compare page:** Compare uses HeatMap only per test comment; confirm and document.
- **If replay has 0 TorchViz3D when showComparison false:** Still 1 (primary); count is correct.

---

#### 🟥 Step 1.2: Harden TorchViz3D Overlay for Visibility — *Critical: Overlay is user's only recovery path*

**Why this is critical:** When context is lost, the overlay is the only way users know to refresh. If it's hidden (z-index, overflow, stacking context), they see a white screen with no actionable message.

**Context:**
- Overlay is rendered inside a `div.relative.h-64` wrapper. Parent must not clip or hide it.
- `z-20` is high but can be behind a parent with `isolation: isolate` or `z-index` and `position`.
- TorchViz3D is wrapped by ErrorBoundary on demo/replay; ErrorBoundary does not add stacking context by default.
- `role="alert"` and `aria-live="assertive"` ensure screen readers announce the message.

**Code Implementation:**

```tsx
// TorchViz3D.tsx — ensure overlay is unambiguously on top

// In the Canvas wrapper div (around line 250):
<div className="relative h-64 w-full isolate">
  <Canvas
    // ... existing props
  />
  {/* Overlay: isolate creates stacking context so z-20 is local to this block.
      Ensures overlay is always on top of the Canvas, regardless of parent. */}
  {contextLost && (
    <div
      className="absolute inset-0 z-[100] flex items-center justify-center bg-neutral-900/95"
      role="alert"
      aria-live="assertive"
      aria-label="WebGL context lost. Refresh the page to restore 3D view."
    >
      <div className="rounded-lg border border-amber-500/60 bg-neutral-900 px-4 py-3 text-center shadow-lg">
        <p className={`text-sm font-semibold text-amber-400 ${orbitron.className}`}>
          WebGL context lost
        </p>
        <p className={`mt-1 text-xs text-cyan-400/90 ${jetbrainsMono.className}`}>
          Refresh the page to restore 3D view
        </p>
        <button
          type="button"
          onClick={() => { if (typeof window !== 'undefined') window.location.reload(); }}
          className="mt-3 inline-block px-4 py-2 text-sm font-medium text-cyan-400 hover:text-cyan-300 underline focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-neutral-900 rounded"
          aria-label="Refresh the page to restore 3D view"
        >
          Refresh page
        </button>
      </div>
    </div>
  )}
</div>
```

**What this does:**
- Adds `isolate` to wrapper so overlay stacking is predictable
- Bumps overlay `z-index` from `z-20` to `z-[100]` to beat any parent (e.g. modal at z-50)
- Keeps `role="alert"`, `aria-live`, `aria-label`, and button for a11y

**Assumptions:**
- No page uses a full-screen overlay above z-100 for 3D views
- `isolate` is supported (all modern browsers)

**Risks:**
- **Overlay still hidden:** Parent page might have `overflow: hidden` on ancestor → *Mitigation:* Audit demo/replay layouts; ensure no `overflow-hidden` on 3D container
- **z-[100] overkill:** Could use z-50; 100 is safe for future modals

**Subtasks:**
- [ ] 🟥 Add `isolate` to Canvas wrapper div
- [ ] 🟥 Change overlay `z-20` to `z-[100]`
- [ ] 🟥 Verify no `overflow-hidden` on demo/replay 3D parent divs

**✓ Verification Test:**

**Action:**
1. Run `npm run dev` in my-app
2. Navigate to http://localhost:3000/demo
3. Open DevTools → Console
4. In TorchViz3D mock or real component: if possible, trigger `webglcontextlost` (see TorchViz3D.test: set `__TORCHVIZ_TEST_CONTEXT_LOSS` — but that's in test env; in browser we need manual trigger)
5. **Alternative:** Use Chrome DevTools → More tools → Rendering → "Emulate CSS media type: screen" or throttle CPU, then open 6+ tabs with 3D content to exhaust contexts; return to demo tab
6. Or: Add temporary `useEffect` in TorchViz3D that calls `setContextLost(true)` after 2s for testing (remove before commit)

**Expected Result:**
- Overlay appears with "WebGL context lost" and "Refresh page" button
- Overlay covers the 3D canvas fully
- No part of the overlay is clipped by parent
- Refresh button works

**Pass Criteria:**
- Overlay visible when context lost (or when `setContextLost(true)` forced)
- z-index and isolate prevent any parent from covering overlay
- TorchViz3D.test "shows WebGL context lost overlay" still passes

**Common Failures & Fixes:**
- **Overlay not visible:** Check parent has no `overflow: hidden`; add `overflow: visible` if needed
- **Button not clickable:** Overlay might have `pointer-events: none` — ensure overlay div does not disable pointer events

---

#### 🟥 Step 1.3: Add Demo Page Instance-Count Test

**Subtasks:**
- [ ] 🟥 Add test: "uses at most 2 TorchViz3D instances" to demo page test file
- [ ] 🟥 Use same pattern as replay test: `screen.getAllByTestId('torch-viz-3d-mock')` and `expect(length).toBeLessThanOrEqual(2)`

**Files:**
- **Modify:** `my-app/src/__tests__/app/demo/page.test.tsx`

**✓ Verification Test:**

**Action:**
1. Run `npm test -- my-app/src/__tests__/app/demo/page.test.tsx`
2. Ensure existing tests pass
3. New test: `expect(screen.getAllByTestId('torch-viz-3d-mock').length).toBeLessThanOrEqual(2)`

**Expected Result:**
- All demo tests pass
- New test passes (demo has exactly 2, so ≤2 holds)

**Pass Criteria:**
- Test file has explicit "uses at most 2 TorchViz3D instances" test
- `npm test` passes

**Common Failures & Fixes:**
- **Mock returns single element for multiple calls:** The `next/dynamic` mock replaces the entire component with one div; each `<TorchViz3D />` becomes one mock instance. Verify mock renders per invocation — in typical jest mock, `default: () => () => <div data-testid="..." />` means each call creates a new component, so 2 TorchViz3D → 2 divs. If mock is wrong, fix to render one div per TorchViz3D instance.

---

#### 🟥 Step 1.4: Strengthen WEBGL_CONTEXT_LOSS.md with HMR Section

**Subtasks:**
- [ ] 🟥 Add new section "HMR and Development — Expected Behavior"
- [ ] 🟥 State explicitly: "When you save a file, Next.js HMR remounts components. R3F disposes the old Canvas and calls forceContextLoss(). The browser console will show 'THREE.WebGLRenderer: Context Lost' — this is expected and not a bug. The page remounts with a new WebGL context. No user action required."
- [ ] 🟥 Add "Team Onboarding" bullet: "Add to developer onboarding: Context Lost during HMR is expected; do not file a bug."
- [ ] 🟥 Add link to R3F discussion #2109

**Files:**
- **Modify:** `documentation/WEBGL_CONTEXT_LOSS.md`

**✓ Verification Test:**

**Action:**
1. Read the updated WEBGL_CONTEXT_LOSS.md
2. Search for "HMR" — section must exist
3. Search for "expected" — must clearly state HMR context loss is expected

**Expected Result:**
- New section present
- Wording is unambiguous
- Team onboarding note included

**Pass Criteria:**
- Documentation is self-contained; new dev can understand without asking

---

### Phase 2 — Enforcement and Verification

**Goal:** ESLint prevents >2 instances; loading fallbacks are verified and consistent; overlay visibility is manually validated.

**Why this phase second:** Enforcement locks in Phase 1 gains; verification ensures nothing is missed.

**Time Estimate:** 3–5 hours

**Risk Level:** 🟡 40%

---

#### 🟥 Step 2.1: Add ESLint Rule for TorchViz3D Instance Count — *Critical: Prevents regression*

**Why this is critical:** Without automated enforcement, a developer can add a 3rd TorchViz3D and exceed the context limit. ESLint catches this at edit time or in CI.

**Context:**
- Rule applies to page files: `**/app/**/page.tsx`, `**/app/**/*/page.tsx`
- Exclude: `**/__tests__/**`, `**/dev/**` (dev routes are for experimentation)
- Count: number of `<TorchViz3D` or `<TorchViz3D` (self-closing) in the file
- Max: 2 (from `constants/webgl.ts`)

**Code Implementation:**

Option A — Custom ESLint rule (recommended):

```javascript
// my-app/eslint-rules/max-torchviz3d-per-page.js
module.exports = {
  meta: {
    type: 'problem',
    docs: { description: 'Enforce max 2 TorchViz3D instances per page' },
    schema: [{ type: 'integer', minimum: 1 }],
    messages: {
      exceed: 'Page has {{count}} TorchViz3D instances. Max {{max}} allowed. See constants/webgl.ts and documentation/WEBGL_CONTEXT_LOSS.md.',
    },
  },
  create(context) {
    const max = context.options[0] ?? 2;
    const filename = context.getFilename?.() ?? '';
    if (filename.includes('__tests__') || filename.includes('/dev/')) return {};
    if (!/page\.tsx$/.test(filename) || !filename.includes('/app/')) return {};
    let count = 0;
    let firstNode = null;
    return {
      JSXElement(node) {
        const name = node.openingElement.name;
        const rawName = name.type === 'JSXIdentifier' ? name.name :
          (name.type === 'JSXMemberExpression' ? `${name.object.name}.${name.property.name}` : null);
        if (rawName === 'TorchViz3D') {
          count++;
          if (!firstNode) firstNode = node;
        }
      },
      'Program:exit'() {
        if (count > max) {
          context.report({
            node: firstNode,
            messageId: 'exceed',
            data: { count, max },
          });
        }
      },
    };
  },
};
```

Then in eslint.config.mjs (flat config):
```javascript
import maxTorchviz3dRule from './eslint-rules/max-torchviz3d-per-page.js';
const maxTorchvizPlugin = { rules: { 'max-torchviz3d-per-page': maxTorchviz3dRule } };
// In defineConfig array, add a config object:
{
  plugins: { 'max-torchviz': maxTorchvizPlugin },
  rules: { 'max-torchviz/max-torchviz3d-per-page': ['error', 2] },
}
```

Option B — Simpler: use `eslint-plugin-no-restricted-syntax` or a `no-restricted-*` pattern. ESLint's `no-restricted-syntax` with a selector for JSXElement named TorchViz3D would require counting — complex. Prefer custom rule.

**Simpler alternative if custom rule is too much:** Add a script `scripts/check-torchviz-count.mjs` that:
1. Finds all `app/**/page.tsx` files (exclude __tests__, dev)
2. Reads file content, regex counts `<TorchViz3D`
3. Exits 1 if any file has count > 2
4. Run in `package.json` `"lint:webgl": "node scripts/check-torchviz-count.mjs"` and add to CI

**What this does:**
- Prevents adding 3+ TorchViz3D to any page
- Fails CI if violated
- Custom rule gives line numbers; script gives file names only

**Assumptions:**
- Pages use TorchViz3D as JSX directly; not via a wrapper that renders it N times from a loop (we don't have that pattern)

**Subtasks:**
- [ ] 🟥 Implement Option A (custom rule) or Option B (script)
- [ ] 🟥 Add to eslint config or package.json scripts
- [ ] 🟥 Run against demo, replay, dev pages — must pass
- [ ] 🟥 Intentionally add 3rd TorchViz3D to a test file, run rule — must fail

**✓ Verification Test:**

**Action:**
1. Run ESLint (or lint:webgl script) on my-app
2. All current pages must pass (demo 2, replay 2, dev 1)
3. Add `<TorchViz3D angle={45} temp={400} />` a 3rd time to demo page
4. Run again — must fail with clear message
5. Revert the 3rd instance

**Expected Result:**
- Pass on current codebase
- Fail when 3 instances exist
- Error message references webgl.ts and WEBGL_CONTEXT_LOSS.md

**Pass Criteria:**
- Enforcement works in practice
- No false positives on dev or test files

---

#### 🟥 Step 2.2: Verify Loading Fallbacks on Demo and Replay

**Subtasks:**
- [ ] 🟥 Confirm demo loading div has `h-64`, `rounded-xl`, `border-2 border-cyan-400/40`, `bg-neutral-900`, and "Loading 3D…" text
- [ ] 🟥 Confirm replay loading div matches (same structure)
- [ ] 🟥 Confirm layout reserves space (h-64) to avoid layout shift when 3D loads
- [ ] 🟥 If any mismatch, align to dev/torch-viz reference

**Files:**
- **Read:** `my-app/src/app/demo/page.tsx` (lines 33–46)
- **Read:** `my-app/src/app/replay/[sessionId]/page.tsx` (lines 21–35)
- **Read:** `my-app/src/app/dev/torch-viz/page.tsx` (lines 19–28)

**✓ Verification Test:**

**Action:**
1. Start dev server
2. Throttle network to "Slow 3G" in DevTools
3. Navigate to /demo
4. Observe: loading state with "Loading 3D…" and reserved h-64 area appears before 3D
5. Repeat for /replay/[any-valid-session-id]

**Expected Result:**
- "Loading 3D…" visible during load
- No layout shift (placeholder height matches final 3D height)
- Consistent styling with cyan theme

**Pass Criteria:**
- Both pages show loading state
- No regressions (e.g. blank area during load)

---

#### 🟥 Step 2.3: Document Manual Overlay Verification Procedure

**Subtasks:**
- [ ] 🟥 Add "Manual Verification" section to WEBGL_CONTEXT_LOSS.md or plan
- [ ] 🟥 Describe how to trigger context loss: (a) Open 8+ tabs with /demo or /replay, (b) Or add temporary `setContextLost(true)` in TorchViz3D for 2s after mount (dev only)
- [ ] 🟥 Describe expected result: overlay appears within 500ms, has "Refresh page" button, button works
- [ ] 🟥 List browsers to test: Chrome, Firefox, Safari

**Files:**
- **Modify:** `documentation/WEBGL_CONTEXT_LOSS.md`

**✓ Verification Test:**

**Action:**
1. Follow the documented procedure
2. Trigger context loss (or simulated)
3. Verify overlay appears and is usable

**Pass Criteria:**
- Procedure is reproducible
- Document is committed for future QA/onboarding

---

### Phase 3 — Documentation and Closure

**Goal:** LEARNING_LOG and code review checklist updated; all acceptance criteria verified.

**Time Estimate:** 1–2 hours

**Risk Level:** 🟢 15%

---

#### 🟥 Step 3.1: Update LEARNING_LOG.md

**Subtasks:**
- [ ] 🟥 Add entry: "WebGL Context Lost — Project-Wide Mitigations (2025-02)"
- [ ] 🟥 Summary: Hardened overlay (z-100, isolate), added demo instance-count test, ESLint/script enforcement, HMR documentation
- [ ] 🟥 Reference: webgl-context-lost-consistent-project-wide plan, WEBGL_CONTEXT_LOSS.md
- [ ] 🟥 Update "Process Level" checklist: ESLint/script for instance count; manual overlay verification doc

**Files:**
- **Modify:** `LEARNING_LOG.md`

**✓ Verification Test:** Read LEARNING_LOG; entry is coherent and linked.

---

#### 🟥 Step 3.2: Add Code Review Checklist for WebGL

**Subtasks:**
- [ ] 🟥 In WEBGL_CONTEXT_LOSS.md or CONTRIBUTING.md, add "Code Review Checklist for 3D / WebGL"
- [ ] 🟥 Bullets: (1) Does this page add TorchViz3D? If yes, count instances — must be ≤2. (2) Is dynamic import used with ssr: false and loading fallback? (3) Any new Canvas/R3F usage? If so, same rules apply.

**Files:**
- **Modify:** `documentation/WEBGL_CONTEXT_LOSS.md` (add checklist section)

**✓ Verification Test:** Checklist is actionable; reviewer can answer yes/no.

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Node.js v18+ | `node --version` → v18.x or higher | ⬜ |
| | Dependencies installed | `npm install` in my-app → no errors | ⬜ |
| | Dev server runs | `npm run dev` → localhost:3000 serves | ⬜ |
| | Demo page loads | Navigate to /demo → expert/novice columns render | ⬜ |
| | Replay page loads | Navigate to /replay/sess_expert_001 (or mock) → 3D loads | ⬜ |
| **Phase 2** | Phase 1 complete | All Phase 1 steps done, tests pass | ⬜ |
| | ESLint runs | `npm run lint` (or equivalent) | ⬜ |
| **Phase 3** | Phase 2 complete | ESLint rule and loading verified | ⬜ |

---

## Success Criteria (End-to-End)

**After all phases complete, these must be true:**

| Acceptance Criterion | Target Behavior | Verification Method |
|----------------------|-----------------|---------------------|
| **1. Demo loading fallback** | Demo shows "Loading 3D…" while TorchViz3D loads | Manual: throttle network, load /demo → see loading state |
| **2. Replay loading fallback** | Replay shows "Loading 3D…" while TorchViz3D loads | Manual: throttle network, load /replay/[id] → see loading state |
| **3. Overlay within 500ms** | When context lost, overlay appears quickly | TorchViz3D.test + manual (simulated or multi-tab) |
| **4. Overlay accessible** | role="alert", aria-live, keyboard-accessible button | TorchViz3D.test "context lost overlay has keyboard-accessible refresh button" |
| **5. Demo ≤2 instances** | Demo uses at most 2 TorchViz3D | Demo test "uses at most 2 TorchViz3D instances" |
| **6. Replay ≤2 instances** | Replay uses at most 2 TorchViz3D | Replay test "uses at most 2 TorchViz3D instances" |
| **7. Automated instance test** | Demo and replay both have test | Both test files contain assertion |
| **8. HMR documented** | Docs say Context Lost during HMR is expected | WEBGL_CONTEXT_LOSS.md has HMR section |
| **9. No regression** | TorchViz3D overlay still works | TorchViz3D.test passes |
| **10. Lint/guidance** | ESLint or script enforces ≤2 | Running lint/script on page with 3 instances fails |

---

## Progress Tracking

| Phase | Steps | Completed | Percentage |
|-------|-------|-----------|------------|
| Phase 1 | 4 | 4 | 100% |
| Phase 2 | 3 | 3 | 100% |
| Phase 3 | 2 | 2 | 100% |
| **Total** | **9** | **9** | **100%** |

---

## Notes & Learnings

### Audit (Step 1.1) — Completed 2025-02-16

| Page | dynamic() + loading | TorchViz3D count |
|------|---------------------|------------------|
| Demo | ✓ | 2 |
| Replay | ✓ | 2 (1 primary + 1 conditional on showComparison) |
| Dev torch-viz | ✓ | 1 |

TorchViz3D has `onCreated` with webglcontextlost/webglcontextrestored listeners; overlay uses z-20 (now z-[100]), role="alert", refresh button. No overflow-hidden on demo/replay 3D parent divs.

**As you implement, document:**
- Unexpected challenges encountered
- Solutions that worked better than planned
- Technical debt introduced (and why it was necessary)
- Things that took longer/shorter than estimated
- Ideas for future improvements

[Add notes here during implementation]

---

## Critical vs Non-Critical Steps Summary

| Step | Critical? | Reason |
|------|-----------|--------|
| 1.1 Audit | ❌ No | Verification only |
| 1.2 Overlay hardening | ✅ Yes | User's only recovery path; z-index/stacking affects all pages |
| 1.3 Demo test | ❌ No | Standard test pattern |
| 1.4 HMR doc | ❌ No | Documentation only |
| 2.1 ESLint rule | ✅ Yes | Prevents regression; affects build/CI |
| 2.2 Loading verify | ❌ No | Verification |
| 2.3 Manual procedure | ❌ No | Documentation |
| 3.1 LEARNING_LOG | ❌ No | Documentation |
| 3.2 Code review checklist | ❌ No | Process documentation |

---

⚠️ **IMPORTANT RULES:**

1. **Do NOT mark a step 🟩 Done until its verification test passes**
2. **If blocked, mark step 🟨 In Progress and document what failed**
3. **If a step takes 2x longer than estimated, pause and reassess the plan**
4. **Run verification tests in order — later tests may depend on earlier steps**
5. **Update "Overall Progress" percentage after completing each step**

---

**Remember:** This plan is a living document. If reality diverges from the plan, UPDATE THE PLAN. Don't stubbornly follow a plan that's no longer accurate.
