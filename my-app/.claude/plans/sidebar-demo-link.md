# Plan: Replace AI Nav with Demo Comparison Link + Short URL

**Overall Progress:** `0%` (0 / 2 steps done)

---

## TLDR

The sidebar's "AI Assist" nav item (`/ai`) is being replaced with a "Compare" link that opens the expert-vs-novice aluminium weld comparison at `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`. A short alias `/compare/live` is added via a Next.js redirect so the sidebar never holds the 70-character demo URL. Two files are touched; no new files are created.

---

## Architecture Overview

**The problem this plan solves:**
The sidebar in `src/components/AppSidebar.tsx` has `{ href: "/ai", label: "AI Assist", icon: "◇" }` hardcoded in `PRIMARY_NAV`. The user wants this replaced with a link to the demo comparison page. The target URL (`/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`) is too long to embed directly in the nav constant — any future change to the default sessions would require editing the sidebar. A redirect alias keeps the nav decoupled from the session IDs.

**The pattern applied:**
*Redirect alias (URL indirection).* `next.config.ts` already uses `redirects()` for the `/seagull` → `/dashboard` alias. Adding a second entry follows the established pattern exactly. The sidebar stores only the short alias `/compare/live`; the redirect owns the mapping to the full demo URL. If the demo sessions change in future, only the redirect needs updating — the sidebar is untouched.

**What stays unchanged:**
- `src/app/(app)/ai/page.tsx` — the AI page route is not deleted (just removed from nav). It remains accessible via direct URL.
- `src/app/demo/page.tsx` — the demo landing page and `?autostart=true` redirect are untouched.
- `src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — the comparison page itself is untouched.
- All test files — no component tests cover `AppSidebar` or `next.config.ts`.

**What this plan adds:**
- One new redirect rule in `next.config.ts`: `/compare/live` → `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`, `permanent: false`.
- One modified nav entry in `AppSidebar.tsx` `PRIMARY_NAV`: replaces the AI item with Compare.

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| Short alias `/compare/live` in `next.config.ts` redirects | Embed full URL directly in `PRIMARY_NAV` | Full URL in sidebar couples nav to specific session IDs; future session change requires sidebar edit |
| Short alias `/compare/live` | Use `/demo?autostart=true` as sidebar href | `?autostart=true` only redirects client-side inside `DemoLandingInner` via `router.replace`; server renders the landing page first, causing a flash. Next.js redirect is immediate at the HTTP level. |
| Short alias `/compare/live` | Use `/demo/live` | `/demo/live` would be interpreted by Next.js router as a dynamic segment `[sessionIdA]="live"`, reaching the page with an invalid session ID before the redirect fires. `/compare/live` does not conflict with any dynamic segment. |
| `permanent: false` (302) | `permanent: true` (301) | Permanent redirect is cached by browsers; if sessions change in future, browsers would not re-request. 302 ensures the redirect is re-evaluated on every visit. |
| Icon `⇄` for Compare | Keep `◇` (current AI icon) | `◇` is the existing AI icon; reusing it creates visual identity confusion |

**Known limitations:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| AI page (`/ai`) still exists at its URL | User only asked to remove it from nav, not delete the route | Delete `src/app/(app)/ai/` directory if route is fully deprecated |
| "Compare" nav item is never highlighted as "active" when on the demo page | Demo page is outside `(app)` layout — sidebar is not rendered there | No fix needed; sidebar is invisible on the demo page |

---

## Clarification Gate

All unknowns resolved from codebase reads. No human input required.

| Unknown | Required | Source | Resolved |
|---------|----------|--------|----------|
| Exact target URL | `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` | User message | ✅ |
| Existing redirect pattern in `next.config.ts` | `redirects()` array, `permanent: false` pattern at line 9 | Codebase | ✅ |
| `PRIMARY_NAV` shape | `{ href, label, icon }` `as const` array at lines 14–18 | Codebase | ✅ |
| AI nav entry exact string | `{ href: "/ai", label: "AI Assist", icon: "◇" }` at line 17 | Codebase | ✅ |
| Does `/compare/live` conflict with existing routes? | No — `/compare/[sessionIdA]/[sessionIdB]` only matches two-segment paths; `live` alone is a single segment intercepted by the redirect before it reaches the page router | Codebase | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```bash
# 1. Confirm existing redirect pattern in next.config.ts
grep -n "redirects\|seagull\|permanent" next.config.ts

# 2. Confirm PRIMARY_NAV AI entry (exact anchor for Step 2)
grep -n "PRIMARY_NAV\|ai\|AI Assist" src/components/AppSidebar.tsx

# 3. Confirm /compare/live does not already exist as a redirect
grep -n "compare/live" next.config.ts

# 4. Baseline test count
npx jest --no-coverage 2>&1 | tail -3
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan:       ____
Line count next.config.ts:    24
Line count AppSidebar.tsx:    133
```

**Automated checks (all must pass before Step 1):**
- [ ] `redirects()` function exists in `next.config.ts` — confirms the pattern to extend
- [ ] `{ href: "/ai", label: "AI Assist", icon: "◇" }` appears exactly once in `AppSidebar.tsx`
- [ ] `compare/live` does not appear in `next.config.ts` — confirms Step 1 is not already done
- [ ] `compare/live` does not appear in `AppSidebar.tsx` — confirms Step 2 is not already done

---

## Tasks

### Phase 1 — Add `/compare/live` short URL alias

**Goal:** `GET /compare/live` redirects (302) to `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` at the Next.js server level — no client-side flash.

---

- [ ] 🟥 **Step 1: Add redirect in `next.config.ts`** — *Non-critical: additive change to existing `redirects()` array*

  **Step Architecture Thinking:**

  **Pattern applied:** URL Indirection / Alias. The redirect rule is the single source of truth for which sessions the "live compare" link shows. The sidebar, tests, and any external links all reference `/compare/live`; only this one rule maps it to session IDs.

  **Why this step exists first in the sequence:**
  The sidebar (Step 2) will store `/compare/live` as its `href`. That URL must resolve before the sidebar edit is meaningful. Step 1 must precede Step 2.

  **Why this file is the right location:**
  `next.config.ts` already owns all server-level redirects for this project (the `/seagull` redirect is proof). Adding a second entry in the same `redirects()` array is the minimal, zero-dependency change.

  **Alternative approach considered and rejected:**
  Create `src/app/compare/live/page.tsx` as a client component that calls `router.replace(...)` — rejected because it adds a file, requires a React render cycle before navigation, and shows a loading flash. The `next.config.ts` redirect is immediate at the HTTP level.

  **What breaks if this step deviates:**
  If `permanent: true` is used instead of `permanent: false`, browsers cache the redirect. If sessions change later, users with cached redirects are stuck on stale session IDs until cache expires.

  ---

  **Idempotent:** Yes — adding the same redirect entry twice would not break anything (Next.js uses the first matching rule), but the Pre-Read Gate grep confirms it's absent before editing.

  **Context:** `next.config.ts` currently has one redirect (line 9). This step appends a second entry to the array.

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n "compare/live" next.config.ts`. Must return 0 matches. If 1+ → STOP, already done.
  - Run `grep -n "return \[" next.config.ts`. Must return exactly 1 match (the redirects array). If 0 → STOP.

  **Self-Contained Rule:** All code below is complete and runnable.

  **No-Placeholder Rule:** No `<VALUE>` tokens below.

  ---

  Find the exact existing redirects return block (verbatim — 4 leading spaces, confirmed by pre-read grep):
  ```ts
    return [{ source: "/seagull", destination: "/dashboard", permanent: false }];
  ```
  Replace with:
  ```ts
    return [
      { source: "/seagull", destination: "/dashboard", permanent: false },
      {
        source: "/compare/live",
        destination: "/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001",
        permanent: false,
      },
    ];
  ```

  **What it does:** Adds a 302 redirect so `/compare/live` immediately forwards to the full demo comparison URL at the HTTP level — no React render, no client-side flash.

  **Why this approach:** Follows the exact pattern already established in the file. No new imports, no new helpers.

  **Assumptions:**
  - `next.config.ts` `redirects()` array can hold multiple entries (confirmed by Next.js docs and the existing single-entry pattern)
  - The target path `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` is a valid existing route (user confirmed this is the URL they want to expose)

  **Risks:**
  - Wrong session IDs in destination → redirect goes to 404 demo page → confirm IDs match user's confirmed URL exactly: `sess_expert_aluminium_001_001` and `sess_novice_aluminium_001_001`

  **Git Checkpoint:**
  ```bash
  git add next.config.ts
  git commit -m "feat: add /compare/live redirect to demo comparison page"
  ```

  **Subtasks:**
  - [ ] 🟥 Replace single-item redirect array with two-item array in `next.config.ts`

  **✓ Verification Test:**

  **Type:** Integration (dev server)

  **Action:**
  ```bash
  # 1. Restart the dev server (next.config.ts changes require restart).
  #    Stop the running server, then start it and wait for "Ready in" in the terminal:
  npm run dev
  # Once "Ready in Xs" appears, open a second terminal and run:
  curl -I http://localhost:3000/compare/live
  ```

  **Expected:**
  - `HTTP/1.1 307 Temporary Redirect` or `302 Found`
  - `Location: /demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`
  - Old single-entry array no longer present:
    ```bash
    grep "return \[{" next.config.ts
    # Must return 0 matches (old one-liner is gone)
    ```

  **Pass:** `curl -I` shows 302/307 with correct `Location` header.

  **Fail:**
  - If `404` → dev server not running or route conflict → check `src/app/compare/live/` doesn't exist as a directory
  - If `Location` points to wrong URL → session IDs were mistyped → re-read Step 1 code block and verify against user's stated URL

---

### Phase 2 — Update sidebar nav

**Goal:** Sidebar shows "Compare" (with `⇄` icon) instead of "AI Assist", linking to `/compare/live`.

---

- [ ] 🟥 **Step 2: Replace AI nav entry in `AppSidebar.tsx`** — *Non-critical: single-line replace in a `const` array*

  **Step Architecture Thinking:**

  **Pattern applied:** Open/Closed on a data-driven nav constant. `PRIMARY_NAV` is a `as const` array iterated by a single `map()` render. Changing one entry in the array is the only edit needed — no component logic changes.

  **Why this step exists after Step 1:**
  The sidebar will store `/compare/live` as its `href`. That URL must already redirect (Step 1) before the sidebar is deployed, so navigation works end-to-end.

  **Why this file is the right location:**
  `PRIMARY_NAV` in `AppSidebar.tsx` is the single source of truth for all primary sidebar items. It is the only place that needs to change.

  **Alternative approach considered and rejected:**
  Add the Compare item as an additional fourth entry while keeping AI — rejected as out of scope; user explicitly said to replace AI, not add alongside it.

  **What breaks if this step deviates:**
  If the `href` is set to the full demo URL instead of `/compare/live`, the `itemClass` active-state logic (`startsWith`) may spuriously match other `/demo/...` routes if the sidebar is ever rendered in a demo-adjacent context.

  ---

  **Idempotent:** Yes — replacing the same line twice produces the same result.

  **Context:** `PRIMARY_NAV` is defined at lines 14–18 of `AppSidebar.tsx`. The AI entry is on line 17.

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n "compare/live\|AI Assist\|/ai" src/components/AppSidebar.tsx`
    - `"AI Assist"` must appear exactly once. If 0 → STOP (already replaced).
    - `compare/live` must appear 0 times. If 1+ → STOP (already done).

  **Self-Contained Rule:** All code below is complete and runnable.

  **No-Placeholder Rule:** No `<VALUE>` tokens below.

  ---

  Find the exact AI nav entry line (verbatim — 2 leading spaces, confirmed by pre-read grep):
  ```ts
  { href: "/ai",        label: "AI Assist", icon: "◇" },
  ```
  Replace with (note: `/compare/live` is longer than `/ai` so column alignment is intentionally dropped):
  ```ts
  { href: "/compare/live", label: "Compare", icon: "⇄" },
  ```

  **What it does:** Swaps the "AI Assist" nav item for a "Compare" item pointing to the short alias. The `map()` render loop, `itemClass` logic, and collapse behaviour are all unchanged.

  **Why this approach:** One-line change in a data array — zero risk to surrounding component logic.

  **Assumptions:**
  - The `⇄` character renders in the project's monospace font (same font used by `◇`). If it renders as a box, change to any other single Unicode character.
  - `href: "/compare/live"` will never match an active pathname shown while the sidebar is visible (the demo page is outside the `(app)` layout so the sidebar is not rendered there)

  **Risks:**
  - `⇄` icon does not render in the target font → visible as □ → mitigation: dev server visual check; swap to `↔` or `⊞` if needed

  **Git Checkpoint:**
  ```bash
  git add src/components/AppSidebar.tsx
  git commit -m "feat: replace AI Assist nav with Compare link to /compare/live"
  ```

  **Subtasks:**
  - [ ] 🟥 Replace AI entry in `PRIMARY_NAV` with Compare entry

  **✓ Verification Test:**

  **Type:** E2E (dev server visual)

  **Action:**
  1. `npm run dev`
  2. Navigate to `http://localhost:3000/analysis`
  3. Inspect the left sidebar

  **Expected:**
  - "AI Assist" label no longer visible in sidebar
  - "Compare" label visible with `⇄` icon
  - Clicking "Compare" navigates to `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`
  - Confirm old label gone:
    ```bash
    grep "AI Assist" src/components/AppSidebar.tsx
    # Must return 0 matches
    ```

  **Pass:** Sidebar shows "Compare", click opens the demo comparison page.

  **Fail:**
  - "AI Assist" still visible → grep confirms it's still in the file → Edit was not applied → re-read file and reapply
  - Click goes to 404 → Step 1 redirect not applied or dev server not restarted → confirm `next.config.ts` has the `/compare/live` entry and restart `npm run dev`
  - Icon renders as □ → font doesn't support `⇄` → replace with `↔` in the same line

---

## Regression Guard

**Systems at risk:**
- `AppSidebar.tsx` — any test that renders the sidebar and asserts nav items by label will fail if it expects "AI Assist"

**Regression verification:**

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| Sidebar nav | 3 primary items: Analysis, Overview, AI Assist | 3 primary items: Analysis, Overview, Compare |
| `/ai` route | Accessible via sidebar | Still accessible by direct URL; only removed from nav |
| `/compare/live` | 404 | 302 → `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` |
| Existing `/seagull` redirect | 302 → `/dashboard` | Unchanged — confirm with `grep "seagull" next.config.ts` returns 1 match |

**Test count regression check:**
```bash
npx jest --no-coverage 2>&1 | tail -3
# Must show ≥ same passing count as pre-flight baseline
```

---

## Rollback Procedure

```bash
git revert HEAD     # reverts Step 2 (AppSidebar)
git revert HEAD~1   # reverts Step 1 (next.config.ts)

# Confirm:
grep "AI Assist" src/components/AppSidebar.tsx   # must return 1 match
grep "compare/live" next.config.ts               # must return 0 matches
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Short URL works | `GET /compare/live` → 302 to demo URL | `curl -I http://localhost:3000/compare/live` shows correct `Location` header |
| Sidebar updated | "Compare" replaces "AI Assist" | `grep "AI Assist" src/components/AppSidebar.tsx` returns 0; sidebar shows "Compare" |
| Existing `/seagull` redirect unbroken | Still 302 → `/dashboard` | `grep "seagull" next.config.ts` returns 1 match |
| `/ai` route accessible | Still responds at its URL | `curl -I http://localhost:3000/ai` returns 200 |
| Test count | ≥ pre-plan baseline | `npx jest --no-coverage` |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Restart the dev server after editing `next.config.ts` — redirects are evaluated at startup.**
⚠️ **Do not batch both steps into one git commit.**
⚠️ **The `/ai` page is NOT deleted — only removed from the sidebar nav.**
⚠️ **If `⇄` renders as a box in the sidebar, replace with `↔` (U+2194) in `AppSidebar.tsx` only.**
