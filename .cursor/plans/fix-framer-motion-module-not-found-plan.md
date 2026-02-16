# Fix framer-motion Module Not Found — Implementation Blueprint (Enhanced)

## Executive Summary

**Issue:** `Module not found: Can't resolve 'framer-motion'` in `my-app/src/app/(marketing)/page.tsx` when building or running the app.

**Root cause:** `framer-motion` is declared in `package.json` but is absent from `node_modules` (dependencies not installed, or install was incomplete/corrupted).

**Primary fix:** Install dependencies using the project's install command (see Phase 1, Step 1.3).

**Estimated total time:** 15–35 minutes (best case: ~10 min; worst case: ~45 min including escalations).

---

## Pre-Planning Synthesis

### Core Approach

We use a **diagnose-then-fix** approach: validate the current state (package.json, node_modules, project install command), then apply the minimum fix—full install, targeted reinstall, or clean reinstall. If the package exists and looks valid, we skip install phases and check imports/bundler instead.

**Key decisions:**

1. **Phase ordering:** Phase 1 determines the path. Absent/invalid package → Phase 2; valid package → Phase 4.
2. **Install command detection:** Step 1.3 must run before any install. This project uses `npm install --legacy-peer-deps` (from root `install:all`). Plain `npm install` can fail or cause CI drift.
3. **Package manager detection:** Step 1.3 also detects which package manager (npm, pnpm, yarn) from lockfiles; different managers use different commands.
4. **No lockfile removal by default:** Phase 3 keeps `package-lock.json`; removal is a last resort with backup.

### Major Components

1. **Phase 1 (Validate):** `package.json`, `node_modules` validity, install command, package manager.
2. **Phase 2 (Fix Dependencies):** Full install or targeted `framer-motion` reinstall.
3. **Phase 3 (Clean Reinstall):** Remove `node_modules` (and only if needed, lockfile), reinstall.
4. **Phase 4 (Import/Path):** Verify imports and build context when package exists but build fails.
5. **Phase 5 (Bundler/Config):** `transpilePackages`, aliases, peer conflicts, escalation.

### Data Flow

```
Input: package.json (framer-motion declared) + node_modules state
  ↓
Transform: Detect install command, package manager, validity
  ↓
Process: Install / reinstall / clean install / fix imports / bundler config
  ↓
Output: npm run build exits 0, no framer-motion errors
```

### Risks

1. **Wrong install command:** Plain `npm install` vs `--legacy-peer-deps` → peer conflicts, CI drift.
2. **Wrong package manager:** Using npm in a pnpm project → wrong resolution, broken build.
3. **Destructive actions:** Removing lockfile without backup → version drift.
4. **Branch confusion:** User forgets Phase 1.2 decision and goes to Phase 2 when they should go to Phase 4.

### Gaps Exploration Did Not Address

1. Exact lockfile structure for this monorepo (root vs `my-app`).
2. Whether `framer-motion` v11 has known issues with Next.js 16 / React 19.
3. CI workflow details for automated verification.

---

## Phase 1: Validate Root Cause (2–4 min)

**Goal:** Determine whether the problem is a missing/broken package (→ Phase 2) or an import/path/bundler issue (→ Phase 4).

**Why first:** Correct branching avoids unnecessary reinstall or wasted diagnostic steps.

**Delivered value:** Clear decision point with no ambiguity.

---

### Step 1.1 — Confirm framer-motion in package.json

**What:** Verify `framer-motion` is declared in `my-app/package.json`.

**Why:** If it's missing, add it before install; if present, proceed to node_modules check.

**Files:** Read `my-app/package.json`.

**Verification:**

1. Run `rg "framer-motion" my-app/package.json` (or `grep "framer-motion" my-app/package.json`).
2. **Expect:** A line such as `"framer-motion": "^11.0.0"` in `dependencies`.
3. **Pass:** Entry exists; note the version.

**If absent:** Add `"framer-motion": "^11.0.0"` to `dependencies`, then continue. Document this in implementation notes.

**Time estimate:** 1 min.

---

### Step 1.2 — Inspect node_modules

**What:** Check whether `framer-motion` exists under `my-app/node_modules/framer-motion` and is usable.

**Why:** Determines whether to run install (Phase 2) or import/config checks (Phase 4).

**Validity:** A package is **INVALID** if any of these apply:

- `my-app/node_modules/framer-motion` does not exist
- `my-app/node_modules/framer-motion/package.json` is missing
- Both `dist/` and `lib/` are missing
- Both `dist/` and `lib/` exist but are empty
- Symlinks (if any) are broken

**Verification commands:**

```bash
ls my-app/node_modules/framer-motion
ls my-app/node_modules/framer-motion/package.json
ls my-app/node_modules/framer-motion/dist 2>/dev/null || ls my-app/node_modules/framer-motion/lib 2>/dev/null
```

**Pass:** Directory exists; package.json exists; at least one of `dist/` or `lib/` exists and has content.

**Branching:**

| Condition | Next Action |
|-----------|-------------|
| **Package absent or INVALID** | → Complete Step 1.3, then **go to Phase 2** |
| **Package present and valid** | → Complete Step 1.3, then **go to Phase 4** |

**Time estimate:** 1 min.

---

### Step 1.3 — Determine project install command and package manager

**What:** Before any install, detect (a) which package manager to use, (b) the exact install command and flags.

**Why:** Using the wrong manager (e.g. npm in a pnpm project) or wrong flags (e.g. omitting `--legacy-peer-deps`) can fail or cause CI drift.

**Action:**

1. **Package manager:** Check for lockfiles in `my-app/` (or project root if monorepo):
   - `package-lock.json` → **npm**
   - `pnpm-lock.yaml` → **pnpm**
   - `yarn.lock` → **yarn**
2. **Install command:**
   - Root `package.json` scripts: `install:all`, `setup`, etc.
   - `README.md`, `QUICK_START.md`, docs
   - `.github/workflows/*.yml` for CI install commands

**Expected:** A documented `$INSTALL` and `$PM` (package manager).

**Example for this project:**

- Lockfile: `my-app/package-lock.json` → npm
- Root script: `install:all` runs `cd my-app && npm install --legacy-peer-deps`
- **$INSTALL =** `npm install --legacy-peer-deps` (run from `my-app/`)
- **$PM =** npm

**Package-manager–specific add commands (for Phase 2.2):**

| $PM | Add single package |
|-----|--------------------|
| npm | `npm install framer-motion [same flags]` |
| pnpm | `pnpm add framer-motion` |
| yarn | `yarn add framer-motion` |

**Verification:** Document `$INSTALL` and `$PM`; use them consistently in Phases 2 and 3.

**Time estimate:** 1–2 min.

---

### ⬜ DECISION POINT (End of Phase 1)

**Before starting Phase 2 or Phase 4:**

- [ ] Step 1.1 passed (framer-motion in package.json)
- [ ] Step 1.2 completed (validity assessed)
- [ ] Step 1.3 completed (`$INSTALL` and `$PM` documented)

**→ DECISION — Choose ONE path:**

| Step 1.2 result | Action |
|------------------|--------|
| **Absent or INVALID** | **GO TO Phase 2** (Fix Dependencies). Do NOT go to Phase 4. |
| **Present and valid** | **SKIP Phases 2–3. GO TO Phase 4** (Import & Path Checks) now. |

**Reminder:** If the package is present and valid, the error is likely import/path/bundler-related—skip reinstall and go straight to Phase 4.

**Phase 1 Total Time:** 2–4 min.

---

## Phase 2: Fix Dependencies (3–7 min)

**Use when:** Phase 1.2 found framer-motion absent or invalid.

**Use $INSTALL and $PM from Step 1.3.**

---

### Step 2.1 — Full install

**What:** Run full dependency install from `my-app/` using `$INSTALL`.

**Why:** Restores missing or incomplete `node_modules`.

**Action:**

```bash
cd my-app && $INSTALL
```

Example: `cd my-app && npm install --legacy-peer-deps`

**Verification:** `cd my-app && npm run build` exits 0; output has no "Module not found: framer-motion".

**Time estimate:** 2–4 min.

---

### Step 2.2 — Reinstall framer-motion if Step 2.1 fails

**What:** Force reinstall of `framer-motion` only, with the same flags as `$INSTALL`.

**Why:** Handles corrupted or partially cached installs.

**Action (by package manager):**

| $PM | Command |
|-----|---------|
| npm | `cd my-app && npm install framer-motion --legacy-peer-deps` (use same flags as $INSTALL) |
| pnpm | `cd my-app && pnpm add framer-motion` |
| yarn | `cd my-app && yarn add framer-motion` |

**Verification:** Same as 2.1 — `npm run build` exits 0, no framer-motion errors.

**Dependencies:** Step 2.1 did not resolve the issue.

**Time estimate:** 1–2 min.

**Phase 2 Total Time:** 3–7 min.

---

## Phase 3: Clean Reinstall (5–12 min)

**Use when:** Phase 2 did not fix the error.

**Use $INSTALL from Step 1.3.**

---

### Step 3.1 — Remove node_modules (preferred)

**What:** Delete only `my-app/node_modules`, keeping lockfile.

**Why:** Clean slate without version drift from lockfile removal.

**Safeguards:**

- Run `git status my-app/package.json my-app/package-lock.json`
- If modified: stash or commit before proceeding.

**Action:** `cd my-app && rm -rf node_modules`

**Verification:** `ls my-app/node_modules` fails; `ls my-app/package-lock.json` succeeds.

**Time estimate:** <1 min.

---

### Step 3.2 — Fresh install

**What:** Run `$INSTALL` from `my-app/`.

**Action:** `cd my-app && $INSTALL`

**Verification:** `cd my-app && npm run build` exits 0, no framer-motion errors.

**Time estimate:** 3–5 min.

---

### Step 3.3 — Last resort: remove lockfile (only if 3.2 fails)

**When:** Step 3.2 completed but build still fails with framer-motion errors.

**Risk:** Version drift across environments and CI.

**Action:**

1. Backup: `cp my-app/package-lock.json my-app/package-lock.json.bak`
2. `cd my-app && rm -rf node_modules package-lock.json`
3. `cd my-app && $INSTALL`

**Verification:** `cd my-app && npm run build` exits 0, no framer-motion errors.

**Optional (corrupted cache):** Before 3.2, run `npm cache clean --force` if installs repeatedly fail.

**Phase 3 Total Time:** 5–12 min (3.1: <1 min; 3.2: 3–5 min; 3.3 if needed: +5–7 min).

---

## Phase 4: Import & Path Checks (3–6 min)

**Use when:**

- **(a)** Phase 1.2 found framer-motion **present and valid** — skip Phases 2–3 and go directly here; or
- **(b)** Phase 3 did not resolve the error.

---

### Step 4.1 — Verify imports

**What:** Confirm all framer-motion imports use the correct package name and path.

**Action:** `rg "framer-motion" my-app/src -g "*.{ts,tsx}"` (or `grep -r "framer-motion" my-app/src`).

**Expected:** Imports use `from "framer-motion"` or `from 'framer-motion'` with no typos or custom aliases.

**Verification:** No typos (e.g. `framer-mtion`); no wrong paths; no aliases that override resolution.

**Time estimate:** 1 min.

---

### Step 4.1.1 — Fix incorrect imports (conditional; only if 4.1 finds problems)

**When:** Step 4.1 found incorrect imports.

**Action:** For each incorrect import:

- Fix typos (e.g. `framer-mtion` → `framer-motion`)
- Change wrong paths to `"framer-motion"`
- Remove custom aliases; use `from "framer-motion"` as appropriate.

**Verification:** Rerun 4.1; all imports correct; `cd my-app && npm run build` exits 0.

**Time estimate:** 1–2 min.

---

### Step 4.2 — Check build context

**What:** Ensure build runs from the directory where `framer-motion` is resolvable.

**Action:** Confirm whether `my-app` is the workspace root or nested. Run `npm run build` from `my-app/` and from workspace root if applicable.

**Expected:** Build succeeds from the correct directory.

**Time estimate:** 1 min.

---

### Step 4.2.1 — Fix wrong build directory (conditional; only if 4.2 finds problems)

**When:** Step 4.2 found that build works from one directory but not another.

**Action:** Use the directory where build succeeds. Update CI, scripts, and docs to run build from that directory.

**Verification:** `cd my-app && npm run build` (or equivalent) exits 0; CI uses same command.

**Phase 4 Total Time:** 3–6 min (4.1–4.2: ~2 min; 4.1.1/4.2.1 if needed: +1–4 min).

---

## Phase 5: Bundler and Config (5–15 min)

**Use when:** Phases 1–4 pass or are inapplicable, but build still fails with "Module not found: framer-motion".

---

### Step 5.1 — Next.js transpilePackages

**What:** Add `framer-motion` to `transpilePackages` in Next.js config to help bundler resolution.

**Rationale:** Usually unnecessary; framer-motion ships pre-built ESM. Try when ESM/CJS interop or monorepo hoisting fails.

**Locate config first:** In `my-app/`, check for exactly one of:

- `next.config.ts`
- `next.config.mjs`
- `next.config.js`

Use the file that exists.

**If `next.config.ts` exists (this project):**

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  transpilePackages: ['framer-motion'],
};

export default nextConfig;
```

**If `next.config.mjs` or `next.config.js` exists:**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactCompiler: true,
  transpilePackages: ['framer-motion'],
};

export default nextConfig;
```

**Verification:** `cd my-app && npm run build` exits 0, no framer-motion errors.

**Time estimate:** 2–3 min (locate file: ~1 min; edit: ~1–2 min).

---

### Step 5.2 — Bundler / path aliases

**What:** Ensure no alias overrides `framer-motion` in `next.config.*`, `tsconfig.json`, or `jest.config.js`.

**Action:** Search for `framer-motion` or path aliases; remove or correct any that block resolution.

**Verification:** `cd my-app && npm run build` exits 0.

**Time estimate:** 2–4 min.

---

### Step 5.3 — Peer dependency and version conflicts

**What:** Inspect dependency tree for conflicts.

**Action:** `cd my-app && npm ls framer-motion`

**Expected:** Single resolution; no blocking peer or conflict errors.

**Verification:** Resolve conflicts (dedupe, pin, peer install); `npm run build` exits 0.

**Time estimate:** 2–4 min.

---

### Step 5.4 — Escalation

**Action:**

1. Capture build output: `cd my-app && npm run build 2>&1 | tee build-output.txt`
2. Record environment: `node --version`, `npm --version`, OS
3. Document: commands run, phase path, errors
4. Check Next.js and framer-motion compatibility
5. Open issue or seek support with the above info

**Phase 5 Total Time:** 5–15 min (5.1: 2–3 min; 5.2: 2–4 min; 5.3: 2–4 min; 5.4: as needed).

---

## Pre-Flight Checklist

### Before Phase 1

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node.js 18+ | `node --version` | Install from nodejs.org |
| npm 9+ | `npm --version` | Comes with Node 18+ |
| In project root | `pwd` shows repo root | `cd` to repo root |
| Git clean or stashed | `git status my-app/package*.json` | Stash or commit before Phase 3.1 |

### Before Phase 2

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | Steps 1.1–1.3 done | Complete Phase 1 |
| $INSTALL and $PM documented | Written down | Re-run Step 1.3 |

### Before Phase 4 (when coming from Phase 1.2 valid)

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1.2 passed (valid package) | Node_modules check passed | Re-run 1.2 |
| Step 1.3 complete | $INSTALL documented | Re-run 1.3 |

---

## Risk Heatmap

| Phase | Step | Risk | Probability | Impact | Mitigation |
|-------|------|------|-------------|--------|------------|
| 1 | 1.2 | Wrong validity assessment | Low | High | Use explicit INVALID criteria |
| 1 | 1.3 | Wrong install command | Medium | High | Check lockfile + CI + scripts |
| 2 | 2.1 | Peer conflicts without flags | Medium | High | Use $INSTALL with flags |
| 2 | 2.2 | Wrong add command for PM | Low | High | Use $PM-specific table |
| 3 | 3.1 | Accidental lockfile delete | Low | High | rm only node_modules first |
| 3 | 3.3 | Version drift | Medium | Medium | Backup lockfile first |
| 5 | 5.1 | Wrong config file | Low | Medium | Explicit "locate first" instruction |

---

## Success Criteria

The fix is successful when:

1. `cd my-app && npm run build` exits **0**.
2. There is no "Module not found: framer-motion" in the build output.
3. Next.js produces `.next/` with expected artifacts.
4. `npm run dev` starts without framer-motion errors.
5. `/` (landing page) loads and animations work.

---

## Summary Flow

```
Phase 1 (Validate)
  ├─ 1.1: framer-motion in package.json ✓
  ├─ 1.2: node_modules validity
  │    ├─ Absent/INVALID → Step 1.3 → Phase 2
  │    └─ Present & valid → Step 1.3 → Phase 4
  ├─ 1.3: $INSTALL, $PM (always run before Phase 2 or 4)
  └─ DECISION: If valid → Phase 4; if invalid → Phase 2

Phase 2 (Fix Dependencies)
  ├─ 2.1: $INSTALL
  └─ 2.2: $PM add framer-motion (if 2.1 fails)

Phase 3 (Clean Reinstall) — only if Phase 2 fails
  ├─ 3.1: rm -rf node_modules
  ├─ 3.2: $INSTALL
  └─ 3.3: rm lockfile + $INSTALL (last resort)

Phase 4 (Import/Path) — if Phase 1.2 valid, or Phase 3 failed
  ├─ 4.1: Verify imports
  ├─ 4.1.1: Fix imports (if 4.1 finds issues)
  ├─ 4.2: Check build directory
  └─ 4.2.1: Fix directory (if 4.2 finds issues)

Phase 5 (Bundler) — if Phases 1–4 don’t resolve
  ├─ 5.1: transpilePackages (locate config first)
  ├─ 5.2: Aliases
  ├─ 5.3: Peer deps
  └─ 5.4: Escalation
```

---

## Common Failures & Fixes

| Failure | Detection | Fix |
|---------|-----------|-----|
| Build fails with peer errors | npm install output | Use `--legacy-peer-deps` |
| Wrong package manager | pnpm/yarn project, used npm | Use $PM from Step 1.3 |
| Phase 1.2 valid but still failing | Build fails after Phase 4 | Retry Phase 2.1; then Phase 5 |
| transpilePackages in wrong file | Config not found | Locate config in Step 5.1 first |
| Lockfile deleted without backup | Can't restore | Restore from git; avoid 3.3 unless necessary |

---

## Progress Tracking

| Phase | Steps | Completed | In Progress | Blocked | % |
|-------|-------|-----------+-------------|---------|---|
| Phase 1 | 3 | 0 | 0 | 0 | 0 |
| Phase 2 | 2 | 0 | 0 | 0 | 0 |
| Phase 3 | 3 | 0 | 0 | 0 | 0 |
| Phase 4 | 4 | 0 | 0 | 0 | 0 |
| Phase 5 | 4 | 0 | 0 | 0 | 0 |

---

*Plan version: Enhanced (critique-addressed). Last updated: 2025-02-16.*
