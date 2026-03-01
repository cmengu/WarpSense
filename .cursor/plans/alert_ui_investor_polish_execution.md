# Feature Implementation Plan: Alert UI Investor Polish

**Overall Progress:** `100%`

## TLDR

Replace the cryptic "Haptic → gun" tag on every alert card with "⚡ Real-time alert" and map snake_case backend rule names (e.g. `lack_of_fusion_amps`, `arc_instability`) to human-readable labels across the compare page and realtime page. Investor demos should show professional labels, not internal tooling jargon.

---

## Critical Decisions

- **Shared RULE_LABELS util:** Create `my-app/src/lib/alert-labels.ts` as single source of truth — compare and realtime both import from it. Avoids drift.
- **Haptic tag:** Replace with "⚡ Real-time alert" — keeps the live-feedback indicator without leaking internal jargon. (User allowed "remove entirely" — replacement preferred per issue.)
- **Backend unchanged:** `rule_triggered` stays snake_case; mapping happens at render time only.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Haptic tag: remove vs replace | "⚡ Real-time alert" (replacement) | Issue text: "either remove entirely or replace" — recommend replace | Step 2 | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping: output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read my-app/src/lib/*.ts — list files and confirm no alert-labels.ts exists.
Read my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx lines 580–620 — capture RULE_LABELS and AlertCard structure.
Read my-app/src/app/(app)/realtime/page.tsx lines 103–132 — capture AlertPanel and where rule_triggered is rendered.
Grep -n 'rule_triggered=' backend/realtime/alert_engine.py — confirm all rule names.
Run: cd my-app && npm run build 2>&1 | tail -20 — record exit code.
Run: cd backend && python -m pytest -q 2>&1 | tail -5 — record passing test count.
Run: wc -l my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx my-app/src/app/\(app\)/realtime/page.tsx — record line counts.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Build exit code before plan: ____
Backend test count before plan: ____
Line count compare page: ____
Line count realtime page: ____
RULE_LABELS keys currently: rule1, rule2, rule3
Alert engine rule_triggered values: rule1, rule2, rule3, porosity, oxide_inclusion, undercut, lack_of_fusion_amps, lack_of_fusion_speed, burn_through, crater_crack, arc_instability
```

**Automated checks (all must pass before Step 1):**
- [ ] `npm run build` exits 0
- [ ] `RULE_LABELS` at line 582–586 in compare page exists; keys: rule1, rule2, rule3
- [ ] `⚡ Haptic → gun` appears exactly once at line 612 in compare page
- [ ] `alert.rule_triggered` appears in AlertPanel at line 125 in realtime page
- [ ] No `alert-labels.ts` in my-app/src/lib

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| Step 1 | ✅ | ✅ | ✅ | New file only |
| Step 2 | ✅ | ✅ | ✅ | Compare page edit |
| Step 3 | ✅ | ✅ | ✅ | Realtime page edit |

---

## Tasks

### Phase 1 — Alert Labels & UI Polish

**Goal:** Investor-facing alert cards show human-readable rule names and "⚡ Real-time alert" instead of internal labels.

---

- [x] 🟩 **Step 1: Create shared RULE_LABELS util** — *Non-critical*

  **Idempotent:** Yes — creating a new file; re-run overwrites with same content.

  **Context:** Single source of truth for rule name mapping. Compare and realtime pages will import from this file.

  **Pre-Read Gate:**
  - Run `ls my-app/src/lib/`. Confirm `alert-labels.ts` does NOT exist. If it exists → STOP and report.
  - Run `grep -n 'rule_triggered=' backend/realtime/alert_engine.py`. Must find 11 distinct rule_triggered values. Confirm list: rule1, rule2, rule3, porosity, oxide_inclusion, undercut, lack_of_fusion_amps, lack_of_fusion_speed, burn_through, crater_crack, arc_instability.

  **Self-Contained Rule:** All code below is complete. No references to other steps.

  **No-Placeholder Rule:** No `<VALUE>` tokens.

  ```typescript
  // my-app/src/lib/alert-labels.ts
  /** Maps backend rule_triggered (snake_case) to investor-facing human-readable labels. */
  export const RULE_LABELS: Record<string, string> = {
    rule1: 'Thermal asymmetry',
    rule2: 'Torch angle',
    rule3: 'Travel speed',
    porosity: 'Porosity',
    oxide_inclusion: 'Oxide Inclusion',
    undercut: 'Undercut',
    lack_of_fusion_amps: 'Lack of Fusion — Low Current',
    lack_of_fusion_speed: 'Lack of Fusion — High Speed',
    burn_through: 'Burn Through',
    crater_crack: 'Crater Crack Risk',
    arc_instability: 'Arc Instability',
  };

  /** Returns human-readable label for rule_triggered; fallback to raw value if unknown. */
  export function getRuleLabel(ruleTriggered: string): string {
    return RULE_LABELS[ruleTriggered] ?? ruleTriggered;
  }
  ```

  **What it does:** Exports RULE_LABELS and getRuleLabel. Defensive fallback for unknown rules.

  **Why this approach:** Shared util avoids duplicate maps in compare + realtime. getRuleLabel centralizes fallback logic.

  **Assumptions:**
  - All rule_triggered values from alert_engine.py are enumerated above.
  - Future rules can use fallback (raw value) until explicitly added.

  **Risks:**
  - New backend rule not in map → mitigation: fallback displays raw value; add to map in follow-up.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/lib/alert-labels.ts
  git commit -m "step 1: add shared alert rule labels util"
  ```

  **Subtasks:**
  - [ ] 🟥 Create my-app/src/lib/alert-labels.ts with RULE_LABELS and getRuleLabel
  - [ ] 🟥 Verify file imports without error (build or lint)

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd my-app && npm run build 2>&1 | grep -E '(error|Error|Failed)' || echo "build ok"`
  **Expected:** `build ok` (no error lines)
  **Observe:** Build output
  **Pass:** Build completes; no TypeScript errors
  **Fail:** If `error TS2307` → file path wrong or export missing. If other error → check syntax.

---

- [x] 🟩 **Step 2: Update compare page — import labels, replace Haptic tag** — *Non-critical*

  **Idempotent:** Yes — re-run produces same result.

  **Context:** Compare page has local RULE_LABELS and hardcoded "⚡ Haptic → gun". Replace with shared util and "⚡ Real-time alert".

  **Pre-Read Gate:**
  - Run `grep -n 'RULE_LABELS\|Haptic' my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`. Must find:
    - `RULE_LABELS` at lines 582–586 (definition) and 595 (usage)
    - `Haptic` at line 612
  - Run `grep -n "from '@/lib/api'" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`. Confirm import pattern for adding alert-labels.

  **Anchor Uniqueness Check:**
  - Target: `const RULE_LABELS: Record<string, string> = {` — must appear exactly 1 time
  - Target: `<span className="text-xs text-zinc-500">⚡ Haptic → gun</span>` — must appear exactly 1 time

  **Uniqueness-Before-Replace:** Confirm `RULE_LABELS` is not imported from anywhere else in this file before removing local definition.

  ```typescript
  // 1. Add import (near other @/lib imports, e.g. after fetchSessionAlerts import)
  import { getRuleLabel } from '@/lib/alert-labels';

  // 2. DELETE the local RULE_LABELS block (lines 582–586):
  // const RULE_LABELS: Record<string, string> = {
  //   rule1: 'Thermal asymmetry',
  //   rule2: 'Torch angle',
  //   rule3: 'Travel speed',
  // };

  // 3. In AlertCard, change:
  //   const label = RULE_LABELS[alert.rule_triggered] ?? alert.rule_triggered;
  // to:
  const label = getRuleLabel(alert.rule_triggered);

  // 4. Replace:
  //   <span className="text-xs text-zinc-500">⚡ Haptic → gun</span>
  // with:
  <span className="text-xs text-zinc-500">⚡ Real-time alert</span>
  ```

  **What it does:** Uses shared labels; replaces cryptic haptic tag with investor-friendly text.

  **Why this approach:** Minimal edits; single source of truth for labels.

  **Assumptions:**
  - Step 1 created alert-labels.ts with getRuleLabel.
  - No other component in compare page uses RULE_LABELS (grep confirms).

  **Risks:**
  - Import path wrong → mitigation: use `@/lib/alert-labels` (matches project convention).

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 2: compare page use shared labels and real-time alert tag"
  ```

  **Subtasks:**
  - [ ] 🟥 Add import for getRuleLabel
  - [ ] 🟥 Remove local RULE_LABELS
  - [ ] 🟥 Replace label resolution with getRuleLabel(alert.rule_triggered)
  - [ ] 🟥 Replace "⚡ Haptic → gun" with "⚡ Real-time alert"

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `cd my-app && npm run build 2>&1`
  **Expected:** Exit code 0; no TypeScript errors
  **Observe:** Build output
  **Pass:** Build succeeds
  **Fail:** If import error → check path. If RULE_LABELS used elsewhere → grep and fix.

  **Replacement assertion:** `grep -n 'Haptic' my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` must return 0 matches after edit.

---

- [x] 🟩 **Step 3: Update realtime page — use getRuleLabel for rule display** — *Non-critical*

  **Idempotent:** Yes — re-run produces same result.

  **Context:** Realtime AlertPanel shows raw `alert.rule_triggered`. Replace with human-readable label.

  **Pre-Read Gate:**
  - Run `grep -n 'rule_triggered' my-app/src/app/(app)/realtime/page.tsx`. Must find line 125: `{alert.rule_triggered} · {alert.severity}`.
  - Confirm no existing import from `@/lib/alert-labels`.

  **Anchor Uniqueness Check:**
  - Target: `{alert.rule_triggered} · {alert.severity}` — must appear exactly 1 time at line 125.

  ```typescript
  // 1. Add import near top
  import { getRuleLabel } from '@/lib/alert-labels';

  // 2. Replace line 125:
  //   {alert.rule_triggered} · {alert.severity}
  // with:
  {getRuleLabel(alert.rule_triggered)} · {alert.severity}
  ```

  **What it does:** Displays human-readable rule name in realtime alert panel instead of snake_case.

  **Why this approach:** Same pattern as compare page; consistent UX.

  **Assumptions:**
  - Step 1 and 2 complete. getRuleLabel exists.

  **Risks:** None significant.

  **Git Checkpoint:**
  ```bash
  git add "my-app/src/app/(app)/realtime/page.tsx"
  git commit -m "step 3: realtime page use human-readable rule labels"
  ```

  **Subtasks:**
  - [ ] 🟥 Add import for getRuleLabel
  - [ ] 🟥 Replace alert.rule_triggered with getRuleLabel(alert.rule_triggered) in JSX

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `cd my-app && npm run build 2>&1`
  **Expected:** Exit code 0
  **Observe:** Build output
  **Pass:** Build succeeds
  **Fail:** If import error → check path. If getRuleLabel not found → Step 1 incomplete.

---

## Regression Guard

**Systems at risk from this plan:**
- Compare page alert feed — RULE_LABELS removed; must use getRuleLabel
- Realtime alert panel — rule display changed

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|---------------------------|
| Compare AlertCard label | Shows rule1/rule2/rule3 or raw if unknown | Shows same labels (Thermal asymmetry, etc.) or new defect labels |
| Compare AlertCard tag | Shows "⚡ Haptic → gun" | Shows "⚡ Real-time alert" |
| Realtime AlertPanel | Shows `rule_triggered` (snake_case) | Shows human-readable label |
| Backend | Unchanged | `rule_triggered` still snake_case in API; no backend edits |

**Test count regression check:**
- Backend tests before plan (Pre-Flight): `____`
- Backend tests after plan: `cd backend && python -m pytest -q` — must be ≥ baseline
- Frontend build: must pass before and after

---

## Rollback Procedure

```bash
# Reverse order (Step 3 → 2 → 1)
git revert HEAD~0   # Step 3
git revert HEAD~1   # Step 2
git revert HEAD~2   # Step 1

# Or if single branch:
git revert --no-commit HEAD~2..HEAD
git commit -m "rollback: alert UI investor polish"

# Confirm:
cd my-app && npm run build
cd backend && python -m pytest -q
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | alert-labels.ts does not exist | `ls my-app/src/lib/` | ⬜ |
| | RULE_LABELS in compare page | grep finds lines 582–586 | ⬜ |
| | Haptic tag in compare page | grep finds line 612 | ⬜ |
| | rule_triggered in realtime | grep finds line 125 | ⬜ |
| | Build passes | npm run build exit 0 | ⬜ |
| Step 1 | alert-labels.ts created | File exists, exports RULE_LABELS and getRuleLabel | ⬜ |
| Step 2 | Compare page updated | No local RULE_LABELS; Haptic gone; getRuleLabel used | ⬜ |
| Step 3 | Realtime page updated | getRuleLabel used in AlertPanel | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| Step 1 | Low | Path typo, missing export | Build fails on import | Yes |
| Step 2 | Low | Wrong replace scope, leftover RULE_LABELS | Grep Haptic returns 0; build passes | Yes |
| Step 3 | Low | Import path wrong | Build fails | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|---------------|
| Shared labels | RULE_LABELS + getRuleLabel in alert-labels.ts | **Do:** read file **Expect:** 11 rule keys, getRuleLabel function **Look:** my-app/src/lib/alert-labels.ts |
| Compare page | No "Haptic → gun"; human labels | **Do:** grep Haptic compare page **Expect:** 0 matches **Look:** compare page |
| Compare page | "⚡ Real-time alert" on cards | **Do:** grep "Real-time alert" compare page **Expect:** 1 match **Look:** compare page |
| Realtime page | Human-readable rule in AlertPanel | **Do:** grep getRuleLabel realtime page **Expect:** 1 import, 1 usage **Look:** realtime page |
| Regression | Backend unchanged | **Do:** grep rule_triggered backend **Expect:** No edits to backend | N/A |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
⚠️ **If blocked, mark 🟨 In Progress and output the State Manifest before stopping.**
⚠️ **Do not batch multiple steps into one git commit.**
