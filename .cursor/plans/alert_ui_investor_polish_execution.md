# Feature Implementation Plan: Alert Feed Pop-In Pattern

**Overall Progress:** `0%`

## TLDR

Replace the current filter-and-render alert feed with a pop-in pattern: alerts appear the moment `currentTimestamp >= alert.timestamp_ms`, ascending (oldest at top, newest appends at bottom). When a card appears it shows correction status immediately. The dot is reactive — it flips green when `currentTimestamp >= alert.timestamp_ms + alert.corrected_in_seconds * 1000`. Rule name is the hero; correction status is a quiet footer. Applies to demo page first; compare page follows with Tailwind.

---

## Critical Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| Render model | **Pop-in** — filter to fired alerts only | Alerts enter the list when timestamp passes. No pre-rendering, no opacity dims. |
| Sort order | **Ascending** (a.timestamp_ms - b.timestamp_ms) | Timeline fills top-to-bottom. Newest alert appends at bottom. |
| Correction dot | **Reactive** — derived from correctedNow inside card | Card pops in red/amber, flips green when correction timestamp passes. Not a static snapshot. |
| correctedNow | `alert.corrected === true && alert.corrected_in_seconds != null && currentTimestamp != null && currentTimestamp >= alert.timestamp_ms + alert.corrected_in_seconds * 1000` | Uses actual AlertPayload fields; null-guards corrected_in_seconds. |
| Count badge | Fired count — `alerts.filter(a => currentTimestamp != null && a.timestamp_ms <= currentTimestamp).length` | Numerically identical to old visibleAlerts.length at any playback position. |
| Scope | Demo first (inline styles, C, FONT_LABEL, FONT_DATA); compare second (Tailwind) | Isolates risk. Same logic, different styling. |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping: output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```bash
# Confirm AlertPayload type exists with expected fields
grep -n "export interface AlertPayload" my-app/src/lib/api.ts

# Confirm corrected and corrected_in_seconds fields exist on AlertPayload
grep -n "corrected" my-app/src/lib/api.ts

# Confirm visibleAlertsA definition in demo page
grep -n "visibleAlertsA" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx

# Confirm visibleAlertsA/B in compare page — record all usages
grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx

# Confirm AlertCard location in demo page
grep -n "AlertCard\|FONT_LABEL\|FONT_DATA" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx | head -20

# Record line counts before changes
wc -l my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
wc -l my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx

# Build must pass before any changes
cd my-app && npm run build 2>&1 | tail -20
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Build exit code before plan: ____
Line count demo page: ____
Line count compare page: ____
AlertPayload fields confirmed: frame_index, rule_triggered, severity, message, correction, timestamp_ms, corrected?, corrected_in_seconds?
visibleAlertsA usages in compare page: ____ (list all line numbers)
```

**Automated checks (all must pass before Step 1a):**
- [ ] `npm run build` exits 0
- [ ] `export interface AlertPayload` found in my-app/src/lib/api.ts
- [ ] `corrected_in_seconds` field confirmed on AlertPayload
- [ ] `visibleAlertsA` found in demo page (useMemo, descending sort)
- [ ] `C`, `FONT_LABEL`, `FONT_DATA` confirmed defined in demo page scope

---

## Tasks

### Phase 1 — Demo Page

---

- [ ] 🟥 **Step 1a: Add AlertFeedColumn to demo page — component only, no grid changes** — *Critical*

  **Idempotent:** Yes — adding a new function; re-run overwrites with same content.

  **Context:** Demo page uses inline styles via C, FONT_LABEL, FONT_DATA constants defined at top of file. AlertFeedColumn replaces the filtering + AlertCard pattern with a pop-in feed. This step adds the component only — no existing code changes.

  **Pre-Read Gate:**
  - Run `grep -n "function AlertCard" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — confirm AlertCard exists and record line number.
  - Run `grep -n "getRuleLabel\|RULE_LABELS" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — confirm getRuleLabel is already in scope (from prior plan). If NOT found, check if it's imported or defined locally and record.
  - Run `grep -n "^const C \|^  C," my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx | head -5` — confirm C is defined.

  **Add AlertFeedColumn immediately before the AlertCard function definition:**

  ```tsx
  function AlertFeedColumn({
    alerts,
    currentTimestamp,
    onSeek,
    error,
    label,
  }: {
    alerts: AlertPayload[];
    currentTimestamp: number | null;
    onSeek: (ts: number) => void;
    error: string | null;
    label: string;
  }) {
    const firedAlerts = alerts
      .filter((a) => currentTimestamp != null && a.timestamp_ms <= currentTimestamp)
      .sort((a, b) => a.timestamp_ms - b.timestamp_ms);

    if (error) {
      return (
        <div style={{ padding: '8px', color: C.textMuted, ...FONT_LABEL }}>
          {error}
        </div>
      );
    }

    if (firedAlerts.length === 0) {
      return (
        <div style={{ padding: '8px', color: C.textMuted, ...FONT_LABEL }}>
          No alerts yet
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {firedAlerts.map((alert) => {
          const correctedNow =
            alert.corrected === true &&
            alert.corrected_in_seconds != null &&
            currentTimestamp != null &&
            currentTimestamp >= alert.timestamp_ms + alert.corrected_in_seconds * 1000;

          const dotColor = correctedNow
            ? '#22c55e'
            : alert.severity === 'critical'
            ? '#ef4444'
            : '#f59e0b';

          return (
            <div
              key={`${alert.timestamp_ms}-${alert.rule_triggered}`}
              onClick={() => onSeek(alert.timestamp_ms)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '6px 8px',
                borderRadius: '6px',
                background: C.surfaceSubtle,
                cursor: 'pointer',
              }}
            >
              {/* Pulse dot */}
              <div
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: dotColor,
                  marginTop: '4px',
                  flexShrink: 0,
                  transition: 'background 0.3s ease',
                }}
              />

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Rule label — hero */}
                <div style={{ ...FONT_LABEL, color: C.text, fontWeight: 600 }}>
                  {getRuleLabel(alert.rule_triggered)}
                </div>

                {/* Timestamp + severity */}
                <div style={{ ...FONT_LABEL, color: C.textMuted, marginTop: '1px' }}>
                  {new Date(alert.timestamp_ms).toISOString().substr(11, 8)} · {alert.severity}
                </div>

                {/* Message */}
                {alert.message && (
                  <div style={{ ...FONT_LABEL, color: C.textMuted, marginTop: '2px' }}>
                    {alert.message}
                  </div>
                )}

                {/* Correction footer */}
                <div
                  style={{
                    fontSize: '7.5px',
                    color: correctedNow ? '#22c55e' : C.textMuted,
                    marginTop: '3px',
                    letterSpacing: '0.02em',
                  }}
                >
                  {correctedNow
                    ? `Corrected in ${alert.corrected_in_seconds?.toFixed(1)}s`
                    : alert.corrected === false
                    ? 'Not corrected'
                    : ''}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  ```

  **What it does:** Filters to fired alerts, sorts ascending, renders each with reactive dot and correction footer. No opacity or pre-rendering.

  **Assumptions:**
  - `C.surfaceSubtle`, `C.text`, `C.textMuted` exist in C object. If any are missing, use closest available equivalent from C and note in report.
  - `getRuleLabel` is in scope in this file.
  - `AlertPayload` is imported from `@/lib/api`.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 1a: add AlertFeedColumn pop-in component to demo page"
  ```

  **Subtasks:**
  - [ ] 🟥 Add AlertFeedColumn function before AlertCard in demo page
  - [ ] 🟥 Confirm file compiles

  **✓ Verification:**

  **Type:** Compile
  **Action:** `cd my-app && npx tsc --noEmit 2>&1 | grep -E '(error TS|Error)' || echo "tsc ok"`
  **Expected:** `tsc ok`
  **Pass:** No TypeScript errors
  **Fail:** If `error TS2339` on C property → check C object keys and use correct one. If `error TS2304` on getRuleLabel → confirm import/definition. One fix, re-run.

---

- [ ] 🟥 **Step 1b: Replace right-panel grid, update count badge, remove visibleAlertsA/B** — *Critical*

  **Idempotent:** Yes.

  **Context:** Wire up AlertFeedColumn in the two-column right panel. Update the header count badge to use fired count. Remove visibleAlertsA/visibleAlertsB from the display layer (keep nothing that depended on them for display).

  **Pre-Read Gate:**
  - Run `grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — list ALL usages. Categorise each: (a) definition/useMemo, (b) display map, (c) count badge, (d) other. Do not proceed if any usage is uncategorised.
  - Run `grep -n "alertsErrorA\|alertsErrorB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — confirm error state variable names.
  - Run `grep -n "setCurrentTimestamp\|setIsPlaying" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx | head -5` — confirm setter names.

  **Anchor Uniqueness Check (run before edit):**
  - `visibleAlertsA.map` — must appear exactly 1 time
  - `visibleAlertsB.map` — must appear exactly 1 time
  - Count badge line (e.g. `visibleAlertsA.length`) — must appear exactly 1 time per badge

  **Changes:**

  **1. Replace the two column divs (Session A / Session B) with AlertFeedColumn:**
  ```tsx
  // Replace Session A column inner content:
  <AlertFeedColumn
    alerts={alertsA}
    currentTimestamp={currentTimestamp}
    onSeek={(ts) => { setCurrentTimestamp(ts); setIsPlaying(false); }}
    error={alertsErrorA}
    label="Session A"
  />

  // Replace Session B column inner content:
  <AlertFeedColumn
    alerts={alertsB}
    currentTimestamp={currentTimestamp}
    onSeek={(ts) => { setCurrentTimestamp(ts); setIsPlaying(false); }}
    error={alertsErrorB}
    label="Session B"
  />
  ```

  **2. Update count badges to fired count:**
  ```ts
  // Session A badge:
  alertsErrorA ? '—' : alertsA.filter(a => currentTimestamp != null && a.timestamp_ms <= currentTimestamp).length

  // Session B badge:
  alertsErrorB ? '—' : alertsB.filter(a => currentTimestamp != null && a.timestamp_ms <= currentTimestamp).length
  ```

  **3. Remove visibleAlertsA and visibleAlertsB useMemo definitions** — delete both blocks entirely.

  **4. Check AlertCard:** Run `grep -n "AlertCard" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` after changes. If AlertCard is now unused, remove the function definition. If still used elsewhere, leave it.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 1b: wire AlertFeedColumn into demo grid, update badge, remove visibleAlerts"
  ```

  **Subtasks:**
  - [ ] 🟥 Replace Session A and B column display content with AlertFeedColumn
  - [ ] 🟥 Update count badges to fired count filter
  - [ ] 🟥 Remove visibleAlertsA and visibleAlertsB useMemo
  - [ ] 🟥 Remove AlertCard if unused

  **✓ Verification:**

  **Type:** Compile + Runtime
  **Action 1:** `cd my-app && npx tsc --noEmit 2>&1 | grep -E '(error TS|Error)' || echo "tsc ok"`
  **Expected:** `tsc ok`

  **Action 2:** `grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx`
  **Expected:** 0 matches

  **Action 3:** Load `/demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`
  - At t=0: alert feed shows "No alerts yet"
  - Advance playback past first alert timestamp: card pops in, dot is red or amber
  - Advance past correction timestamp of a corrected alert: dot flips green, footer reads "Corrected in X.Xs"
  - Count badge increments as alerts fire
  - Click a card: playback seeks to that alert's timestamp

  **Pass:** All runtime checks pass, 0 visibleAlerts grep matches, tsc ok
  **Fail:** If visibleAlerts still appears → grep all usages and remove remaining. If dot never turns green → check corrected_in_seconds is not null in test data.

---

### Phase 2 — Compare Page

---

- [ ] 🟥 **Step 2: Compare page — same pop-in pattern with Tailwind** — *Critical*

  **Idempotent:** Yes.

  **Context:** Compare page mirrors the demo pattern but uses Tailwind classes. Also has critical flash logic (`columnACriticalFlash` / `columnBCriticalFlash`) which depended on `visibleAlertsA/B`. Replace display usage with unfiltered arrays; derive `firedAlertsA`/`firedAlertsB` for flash logic and count badge only.

  **Pre-Read Gate:**
  - Run `grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — list ALL usages. Categorise each: (a) definition, (b) display map, (c) count badge, (d) critical flash, (e) prevVisibleIds. Record every line number.
  - Run `grep -n "columnACriticalFlash\|columnBCriticalFlash\|prevVisibleIds" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — capture full critical flash logic.
  - Run `grep -n "AlertCard" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — record AlertCard definition and usage line numbers.
  - Run `grep -n "AlertPayload\|from '@/lib/api'" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — confirm import pattern.

  **Anchor Uniqueness Check:**
  - `visibleAlertsA.map` — must appear exactly 1 time
  - `visibleAlertsB.map` — must appear exactly 1 time

  **Changes:**

  **1. Add firedAlertsA and firedAlertsB derived values** (for flash + badge only — NOT for display):
  ```ts
  const firedAlertsA = alertsA.filter(
    (a) => floorTs != null && a.timestamp_ms <= floorTs
  );
  const firedAlertsB = alertsB.filter(
    (a) => floorTs != null && a.timestamp_ms <= floorTs
  );
  ```

  **2. Update critical flash logic:** Replace every `visibleAlertsA` reference inside flash logic with `firedAlertsA`. Replace every `visibleAlertsB` with `firedAlertsB`. Same for `prevVisibleIds` if it references visibleAlerts — update to use firedAlerts.

  **3. Update count badges:**
  ```ts
  // Column A badge:
  alertsErrorA ? '—' : firedAlertsA.length

  // Column B badge:
  alertsErrorB ? '—' : firedAlertsB.length
  ```

  **4. Add AlertFeedColumn (Tailwind version) before AlertCard:**
  ```tsx
  function AlertFeedColumn({
    alerts,
    currentTimestamp,
    onSeek,
    error,
  }: {
    alerts: AlertPayload[];
    currentTimestamp: number | null;
    onSeek: (ts: number) => void;
    error: string | null;
  }) {
    const firedAlerts = alerts
      .filter((a) => currentTimestamp != null && a.timestamp_ms <= currentTimestamp)
      .sort((a, b) => a.timestamp_ms - b.timestamp_ms);

    if (error) {
      return <div className="p-2 text-xs text-zinc-500">{error}</div>;
    }

    if (firedAlerts.length === 0) {
      return <div className="p-2 text-xs text-zinc-500">No alerts yet</div>;
    }

    return (
      <div className="flex flex-col gap-1.5">
        {firedAlerts.map((alert) => {
          const correctedNow =
            alert.corrected === true &&
            alert.corrected_in_seconds != null &&
            currentTimestamp != null &&
            currentTimestamp >= alert.timestamp_ms + alert.corrected_in_seconds * 1000;

          const dotClass = correctedNow
            ? 'bg-green-500'
            : alert.severity === 'critical'
            ? 'bg-red-500'
            : 'bg-amber-500';

          return (
            <div
              key={`${alert.timestamp_ms}-${alert.rule_triggered}`}
              onClick={() => onSeek(alert.timestamp_ms)}
              className="flex items-start gap-2 px-2 py-1.5 rounded-md bg-zinc-800 cursor-pointer hover:bg-zinc-700 transition-colors"
            >
              {/* Pulse dot */}
              <div
                className={`w-[7px] h-[7px] rounded-full mt-1 shrink-0 transition-colors duration-300 ${dotClass}`}
              />

              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* Rule label — hero */}
                <div className="text-xs font-semibold text-zinc-100">
                  {getRuleLabel(alert.rule_triggered)}
                </div>

                {/* Timestamp + severity */}
                <div className="text-xs text-zinc-500 mt-0.5">
                  {new Date(alert.timestamp_ms).toISOString().substr(11, 8)} · {alert.severity}
                </div>

                {/* Message */}
                {alert.message && (
                  <div className="text-xs text-zinc-500 mt-0.5">{alert.message}</div>
                )}

                {/* Correction footer */}
                <div
                  className={`mt-0.5 ${correctedNow ? 'text-green-500' : 'text-zinc-600'}`}
                  style={{ fontSize: '7.5px' }}
                >
                  {correctedNow
                    ? `Corrected in ${alert.corrected_in_seconds?.toFixed(1)}s`
                    : alert.corrected === false
                    ? 'Not corrected'
                    : ''}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  ```

  **5. Replace visibleAlertsA.map / visibleAlertsB.map with AlertFeedColumn:**
  ```tsx
  // Column A:
  <AlertFeedColumn
    alerts={alertsA}
    currentTimestamp={floorTs}
    onSeek={(ts) => seekTo(ts)}
    error={alertsErrorA}
  />

  // Column B:
  <AlertFeedColumn
    alerts={alertsB}
    currentTimestamp={floorTs}
    onSeek={(ts) => seekTo(ts)}
    error={alertsErrorB}
  />
  ```
  *(Adjust `seekTo` / `floorTs` to match actual variable names in compare page scope — pre-read gate will confirm.)*

  **6. Remove visibleAlertsA and visibleAlertsB useMemo definitions** — delete both blocks.

  **7. Check AlertCard:** If now unused after step 5, remove the AlertCard function definition.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 2: compare page pop-in alert feed, firedAlerts for flash and badge"
  ```

  **Subtasks:**
  - [ ] 🟥 Add firedAlertsA / firedAlertsB derived values
  - [ ] 🟥 Update critical flash to use firedAlertsA / firedAlertsB
  - [ ] 🟥 Update count badges to firedAlertsX.length
  - [ ] 🟥 Add Tailwind AlertFeedColumn before AlertCard
  - [ ] 🟥 Replace visibleAlertsA.map / visibleAlertsB.map with AlertFeedColumn
  - [ ] 🟥 Remove visibleAlertsA / visibleAlertsB useMemo
  - [ ] 🟥 Remove AlertCard if unused

  **✓ Verification:**

  **Type:** Compile + Grep + Runtime

  **Action 1:** `cd my-app && npx tsc --noEmit 2>&1 | grep -E '(error TS|Error)' || echo "tsc ok"`
  **Expected:** `tsc ok`

  **Action 2:** `grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`
  **Expected:** 0 matches

  **Action 3:** `grep -n "firedAlertsA\|firedAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`
  **Expected:** matches in: definition (×2), badge (×2), critical flash (≥2). No display map usage.

  **Action 4:** Load compare page, advance playback
  - Alerts pop in ascending order
  - Critical column flash still triggers when a critical alert fires
  - Dot flips green at correction timestamp
  - Count badge matches fired count

  **Pass:** All checks pass
  **Fail:** If flash no longer triggers → grep flash logic and confirm firedAlertsA is used not visibleAlertsA. If type error on AlertPayload → confirm import.

---

## Regression Guard

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| Demo alert feed | Filtered list, descending, no correction status | Pop-in, ascending, reactive correction dot + footer |
| Compare alert feed | Same | Same |
| Count badge (both) | `visibleAlerts.length` | `firedAlerts.filter(...).length` — identical value at any playback position |
| Critical flash (compare) | Fires when critical in visibleAlerts | Fires when critical in firedAlertsA/B — same trigger condition |
| Seek on card click | N/A (no click handler on old cards) | Clicking card seeks to alert timestamp |
| Empty state | "No alerts" shown | "No alerts yet" shown when fired count = 0 |

**Regression commands (run after both steps):**
```bash
# No visibleAlerts remaining in display layer
grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 0 matches

grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 0 matches

# firedAlerts used in compare for flash/badge only
grep -n "firedAlertsA\|firedAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: only definition + badge + flash lines; no .map() usage

# Build clean
cd my-app && npm run build 2>&1 | tail -5
# Expected: exit 0
```

---

## Rollback Procedure

```bash
# Reverse order: Step 2 → 1b → 1a
git revert HEAD~0   # Step 2
git revert HEAD~1   # Step 1b
git revert HEAD~2   # Step 1a

# Or single range:
git revert --no-commit HEAD~2..HEAD
git commit -m "rollback: alert feed pop-in pattern"

# Confirm:
cd my-app && npm run build
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | AlertPayload has corrected + corrected_in_seconds | grep fields in api.ts | ⬜ |
| | visibleAlertsA defined in demo page (descending sort) | grep useMemo | ⬜ |
| | All visibleAlerts usages in compare page catalogued | grep lists all lines | ⬜ |
| | C, FONT_LABEL, FONT_DATA confirmed in demo scope | grep confirms | ⬜ |
| | Build passes | npm run build exit 0 | ⬜ |
| Step 1a | AlertFeedColumn added before AlertCard | grep finds function | ⬜ |
| | tsc passes | tsc --noEmit ok | ⬜ |
| Step 1b | Grid uses AlertFeedColumn | grep confirms | ⬜ |
| | visibleAlertsA/B gone from demo | grep returns 0 | ⬜ |
| | Count badge uses fired filter | grep confirms | ⬜ |
| | tsc passes | tsc --noEmit ok | ⬜ |
| Step 2 | firedAlertsA/B defined for flash + badge | grep confirms | ⬜ |
| | visibleAlertsA/B gone from compare | grep returns 0 | ⬜ |
| | Critical flash still uses firedAlerts | grep confirms | ⬜ |
| | tsc passes | tsc --noEmit ok | ⬜ |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|---------------|
| Pop-in render | Alerts appear only when timestamp passes | At t=0: empty feed. Advance: card appears. |
| Ascending order | Oldest at top, newest appends bottom | Verify card order matches timestamp order |
| Reactive dot | Red/amber on pop-in; flips green at correction timestamp | Seek past corrected_in_seconds threshold on a corrected alert |
| Correction footer | "Corrected in X.Xs" or "Not corrected" | Confirm for both corrected=true and corrected=false alerts |
| Rule label hero | getRuleLabel output as primary text | Confirm snake_case is not visible |
| Count badge | Fired count matches | Badge = N at position where N alerts have fired |
| Critical flash (compare) | Still triggers | Advance past a critical alert — column flash fires |
| No regressions | visibleAlerts fully removed from display layer | grep returns 0 matches in both files |

---

⚠️ **Do not mark a step complete until its verification commands all pass.**
⚠️ **Do not proceed to Step 1b until Step 1a tsc check passes.**
⚠️ **Do not proceed to Step 2 until Step 1b runtime checks pass.**
⚠️ **If blocked, output full contents of modified files before stopping.**
⚠️ **Do not batch multiple steps into one git commit.**