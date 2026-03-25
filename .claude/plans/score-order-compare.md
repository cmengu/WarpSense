# Score Display + Higher-Score-Right Ordering on Compare Pages

**Overall Progress:** `100%` (3/3 steps done)

---

## TLDR

Two compare pages need updating:
1. **Demo page** (`/demo/[A]/[B]/page.tsx`, 1520 lines) — WQI scores already render but show `--` when `score_total` is null. Fix: fall back to `MOCK_EXPERT_SCORE_VALUE`/`MOCK_NOVICE_SCORE_VALUE` by session ID pattern. Then swap all left/right column data so higher-score session is always on the right (green column).
2. **Compare page** (`/compare/[A]/[B]/page.tsx`, 655 lines) — no score display at all. Fix: add score badges above each 3D view column; swap columns so higher-score session is always on the right.
3. **Compare page tests** (`page.test.tsx`) — two tests hard-check for `"Session A (...)"` label format which changes in Step 2. Must update.

---

## Architecture Overview

**The problem:**
- Demo page `WQIScore` component renders `value={sessionA?.score_total}` → shows `--` when null (aluminium demo sessions not yet scored via pipeline)
- Demo page left/right column assignment is always URL-order (A=left, B=right) regardless of which session has higher score
- Compare page has zero score display

**Pattern applied:** Derived view variables (computed from loaded state, not stored in state). After sessions load, `swap = scoreA > scoreB` drives which session's data feeds the left vs right render column. No React state change needed — pure render-time derivation, idempotent on re-render.

**What stays unchanged:** All state variables (`sessionA`, `sessionB`, `alertsA`, `alertsB`, flash effects, etc.), all fetch logic, URL routing, `WQIScore` component, `AlertFeedColumn` component.

**What this plan adds:** `leftScore/rightScore/leftId/rightId/leftSession/rightSession/leftAlerts/rightAlerts/...` derived variables used at render sites only.

**Critical decisions:**

| Decision | Alternative | Why rejected |
|---|---|---|
| Fallback scores by session ID pattern (`includes('expert')`) for demo page | Always show `--` if null | User explicitly wants scores always shown; aluminium sessions reliably follow naming convention |
| Compare page: no fallback scores (`null` if unscored) | Same fallback as demo page | Compare page is general-purpose; showing mock values for arbitrary sessions is misleading |
| Compare page: swap only when both scores non-null | Swap on any non-zero score | Prevents wrong ordering when only one session is scored |
| Keep `SESSION_A`/`SESSION_B` mock objects without `score_total` in tests | Add `score_total` to mocks | Keeping them null proves no-swap path and tests continue to cover that case |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) file state, (e) why cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

Run all greps. Record results. Do not edit anything yet.

```
(1) grep -n "MOCK_EXPERT_SCORE_VALUE\|MOCK_NOVICE_SCORE_VALUE" my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx
    → must return 0 matches (not yet imported in demo page)

(2) grep -n "score_total\|wqiGap" my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx
    → record all matches (will verify gone after Step 1)

(3) grep -n "score_total\|leftId\|rightId" my-app/src/app/compare/\[sessionIdA\]/\[sessionIdB\]/page.tsx
    → must return 0 matches (not yet added to compare page)

(4) grep -n "Session A\|Session B" my-app/src/app/compare/\[sessionIdA\]/\[sessionIdB\]/page.test.tsx
    → record exact strings (will be updated in Step 3)
```

---

## Step 1: Demo page — score fallback + swap all column data

**Step Architecture Thinking:**

**Pattern applied:** Derived view variables. All swap logic lives in a single block immediately before the `return` JSX — no state, no effects. The existing state variables (`sessionA`, `sessionB`, etc.) are unchanged; only the render sites are updated to use `leftSession`/`rightSession` etc.

**Why this step exists here:** Demo page already has `WQIScore` component and sparklines — the infrastructure is there, just feeding wrong data.

**Why this file:** Only change needed is in the render layer; no backend or API change required.

**Alternative rejected:** Moving session order responsibility to the URL (redirect if A has higher score than B). Rejected because it changes URLs and breaks existing links.

**What breaks if deviated:** If any render site still references `sessionA?.score_total` directly instead of `leftScore`, that WQI score will show `--` and won't swap.

---

**Idempotent:** Yes — derived variables can be re-derived on every render.

**Files modified:** `my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx`

**Pre-Read Gate:**
- `grep -n "from '@/lib/api'" "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"` → exactly 1 match. If 0 or 2+ → STOP.
- `grep -n "const wqiGap" "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"` → exactly 1 match. If 0 or 2+ → STOP.
- `grep -n "MOCK_EXPERT_SCORE_VALUE" "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"` → must return 0 matches (not yet added). If 1+ → already patched, skip this step.

**Change A — add import for mock score constants:**

Replace:
```tsx
import { fetchSession, fetchSessionAlerts, type AlertPayload } from '@/lib/api';
```
With:
```tsx
import { fetchSession, fetchSessionAlerts, type AlertPayload } from '@/lib/api';
import { MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE } from '@/lib/demo-config';
```

**Change B — replace `wqiGap` with swap block:**

Replace:
```tsx
  const wqiGap =
    sessionA?.score_total != null && sessionB?.score_total != null
      ? Math.abs(Math.round(sessionB.score_total - sessionA.score_total))
      : null;
```
With:
```tsx
  // Score fallback: use mock values when session not yet run through analysis pipeline
  const scoreA = sessionA?.score_total ?? (sessionIdA.toLowerCase().includes('expert') ? MOCK_EXPERT_SCORE_VALUE : MOCK_NOVICE_SCORE_VALUE);
  const scoreB = sessionB?.score_total ?? (sessionIdB.toLowerCase().includes('expert') ? MOCK_EXPERT_SCORE_VALUE : MOCK_NOVICE_SCORE_VALUE);
  // Higher score always on right (green); lower score always on left (red)
  const swap = scoreA > scoreB;
  const leftScore = swap ? scoreB : scoreA;
  const rightScore = swap ? scoreA : scoreB;
  const leftId = swap ? sessionIdB : sessionIdA;
  const rightId = swap ? sessionIdA : sessionIdB;
  const leftSession = swap ? sessionB : sessionA;
  const rightSession = swap ? sessionA : sessionB;
  const leftAlerts = swap ? alertsB : alertsA;
  const rightAlerts = swap ? alertsA : alertsB;
  const leftAlertsError = swap ? alertsErrorB : alertsErrorA;
  const rightAlertsError = swap ? alertsErrorA : alertsErrorB;
  const leftFrame = swap ? currentFrameB : currentFrameA;
  const rightFrame = swap ? currentFrameA : currentFrameB;
  const leftTemp = swap ? currentTempB : currentTempA;
  const rightTemp = swap ? currentTempA : currentTempB;
  const leftHeatHist = swap ? bHeatHist : aHeatHist;
  const rightHeatHist = swap ? aHeatHist : bHeatHist;
  const leftAmpHist = swap ? bAmpHist : aAmpHist;
  const rightAmpHist = swap ? aAmpHist : bAmpHist;
  const leftAngleHist = swap ? bAngleHist : aAngleHist;
  const rightAngleHist = swap ? aAngleHist : bAngleHist;
  const leftFiredCount = swap ? firedCountB : firedCountA;
  const rightFiredCount = swap ? firedCountA : firedCountB;
  const wqiGap = Math.abs(Math.round(rightScore - leftScore));
```

**Change C — sparklines: replace A/B histories with left/right:**

Replace:
```tsx
          <Sparkline
            noviceHistory={aHeatHist}
            expertHistory={bHeatHist}
```
With:
```tsx
          <Sparkline
            noviceHistory={leftHeatHist}
            expertHistory={rightHeatHist}
```

Replace:
```tsx
          <Sparkline
            noviceHistory={aAmpHist}
            expertHistory={bAmpHist}
```
With:
```tsx
          <Sparkline
            noviceHistory={leftAmpHist}
            expertHistory={rightAmpHist}
```

Replace:
```tsx
          <Sparkline
            noviceHistory={aAngleHist}
            expertHistory={bAngleHist}
```
With:
```tsx
          <Sparkline
            noviceHistory={leftAngleHist}
            expertHistory={rightAngleHist}
```

**Change D — Current Values table: replace currentFrameA/B and currentTempA/B:**

Replace:
```tsx
                [
                  'Heat',
                  currentFrameA?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  currentFrameB?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  'kJ/mm',
                ],
                [
                  'Amp',
                  currentFrameA?.amps != null ? String(Math.round(currentFrameA.amps)) : '--',
                  currentFrameB?.amps != null ? String(Math.round(currentFrameB.amps)) : '--',
                  'A',
                ],
                [
                  'Angle',
                  currentFrameA?.angle_degrees != null
                    ? String(Math.round(currentFrameA.angle_degrees))
                    : '--',
                  currentFrameB?.angle_degrees != null
                    ? String(Math.round(currentFrameB.angle_degrees))
                    : '--',
                  '°',
                ],
                [
                  'Temp',
                  currentTempA != null ? String(Math.round(currentTempA)) : '--',
                  currentTempB != null ? String(Math.round(currentTempB)) : '--',
                  '°C',
                ],
```
With:
```tsx
                [
                  'Heat',
                  leftFrame?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  rightFrame?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  'kJ/mm',
                ],
                [
                  'Amp',
                  leftFrame?.amps != null ? String(Math.round(leftFrame.amps)) : '--',
                  rightFrame?.amps != null ? String(Math.round(rightFrame.amps)) : '--',
                  'A',
                ],
                [
                  'Angle',
                  leftFrame?.angle_degrees != null
                    ? String(Math.round(leftFrame.angle_degrees))
                    : '--',
                  rightFrame?.angle_degrees != null
                    ? String(Math.round(rightFrame.angle_degrees))
                    : '--',
                  '°',
                ],
                [
                  'Temp',
                  leftTemp != null ? String(Math.round(leftTemp)) : '--',
                  rightTemp != null ? String(Math.round(rightTemp)) : '--',
                  '°C',
                ],
```

**Change E — WQIScore left (lower score, red):**

Replace:
```tsx
            <WQIScore value={sessionA?.score_total} label="Session A" color={C.novice} />
```
With:
```tsx
            <WQIScore value={leftScore} label={leftId} color={C.novice} />
```

**Change F — wqiGap display (remove `?? '--'` since gap is always a number now):**

Replace:
```tsx
              {wqiGap ?? '--'}
```
With:
```tsx
              {wqiGap}
```

**Change G — WQIScore right (higher score, green):**

Replace:
```tsx
            <WQIScore value={sessionB?.score_total} label="Session B" color={C.expert} />
```
With:
```tsx
            <WQIScore value={rightScore} label={rightId} color={C.expert} />
```

**Change H — 3D circle A (left column): use left session data:**

Replace:
```tsx
                  <TorchWithHeatmap3D
                    angle={currentFrameA?.angle_degrees ?? 67}
                    temp={currentTempA ?? 300}
                    frames={sessionA?.frames ?? []}
```
With:
```tsx
                  <TorchWithHeatmap3D
                    angle={leftFrame?.angle_degrees ?? 67}
                    temp={leftTemp ?? 300}
                    frames={leftSession?.frames ?? []}
```

**Change I — 3D circle B (right column): use right session data:**

Replace:
```tsx
                  <TorchWithHeatmap3D
                    angle={currentFrameB?.angle_degrees ?? 67}
                    temp={currentTempB ?? 300}
                    frames={sessionB?.frames ?? []}
```
With:
```tsx
                  <TorchWithHeatmap3D
                    angle={rightFrame?.angle_degrees ?? 67}
                    temp={rightTemp ?? 300}
                    frames={rightSession?.frames ?? []}
```

**Change J — Alert feed header counts:**

Replace:
```tsx
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 16,
                  fontWeight: 700,
                  color: alertsErrorA ? C.amber : C.novice,
                }}
              >
                A: {alertsErrorA ? '—' : firedCountA}
              </span>
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 16,
                  fontWeight: 700,
                  color: alertsErrorB ? C.amber : C.expert,
                }}
              >
                B: {alertsErrorB ? '—' : firedCountB}
              </span>
```
With:
```tsx
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 16,
                  fontWeight: 700,
                  color: leftAlertsError ? C.amber : C.novice,
                }}
              >
                {leftId}: {leftAlertsError ? '—' : leftFiredCount}
              </span>
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 16,
                  fontWeight: 700,
                  color: rightAlertsError ? C.amber : C.expert,
                }}
              >
                {rightId}: {rightAlertsError ? '—' : rightFiredCount}
              </span>
```

**Change K — AlertFeedColumn left (lower score session):**

Replace:
```tsx
              <AlertFeedColumn
                alerts={alertsA}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={alertsErrorA}
                label="Session A"
              />
```
With:
```tsx
              <AlertFeedColumn
                alerts={leftAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={leftAlertsError}
                label={leftId}
              />
```

**Change L — AlertFeedColumn right (higher score session):**

Replace:
```tsx
              <AlertFeedColumn
                alerts={alertsB}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={alertsErrorB}
                label="Session B"
              />
```
With:
```tsx
              <AlertFeedColumn
                alerts={rightAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={rightAlertsError}
                label={rightId}
              />
```

**Git Checkpoint:**
```bash
git add "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"
git commit -m "feat: demo page — score fallback + swap columns so higher score is always right"
```

**✓ Verification:**

**Type:** Integration (grep) + E2E (browser)

1. Confirm old raw references gone:
   `grep -n "sessionA?.score_total\|sessionB?.score_total\|alertsErrorA\|alertsErrorB\|firedCountA\|firedCountB\|currentFrameA\|currentFrameB\|currentTempA\|currentTempB\|aHeatHist\|bHeatHist" "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"` → must return **0 matches**.

2. Confirm new variables present:
   `grep -n "leftScore\|rightScore\|leftSession\|rightSession\|leftAlerts" "my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx"` → must return matches (the swap block + render sites).

3. E2E: Navigate to `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`.
   - Left WQI score renders a number (not `--`), labeled with the lower-score session ID
   - Right WQI score renders a number (not `--`), labeled with the higher-score session ID
   - The expert session (higher score) is on the **right**, novice on the **left**

**Fail:**
- Step 1 returns matches → a render site was missed — re-read the file, find remaining raw reference, apply change
- WQI still shows `--` → `scoreA`/`scoreB` fallback not triggering — confirm session ID contains `'expert'`/`'novice'` (lowercase check)
- Sessions not swapped → confirm `swap = scoreA > scoreB` evaluates to `true` for expert (score ~94) vs novice (score ~42)

---

## Step 2: Compare page — swap block + score badges + swap column data + fix tests

**Step Architecture Thinking:**

**Pattern applied:** Same derived view variables approach as Step 1. Additionally adds a score badge `<div>` above each 3D view column. No new components needed.

**Why score display differs from demo page:** Compare page is general-purpose (not just aluminium sessions). If `score_total` is null for either session, no swap and no score badge. No mock fallback values.

**Alternative rejected:** Adding a `ScoreBadge` shared component. Rejected because the badge is only 4 lines of inline JSX and a new component adds file bloat with no reuse benefit.

**What breaks if deviated:** If test label assertions aren't updated, CI will fail even though the logic is correct.

---

**Idempotent:** Yes.

**Files modified:** `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`, `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx`

**Pre-Read Gate:**
- `grep -n "const firedAlertsB" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → exactly 1 match. Record line. Swap block inserts immediately after the closing `);` of `firedAlertsB` useMemo.
- `grep -n "Session A (${" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → exactly 2 matches (one per 3D view label). If not 2 → STOP.
- `grep -n "leftId\|rightId\|swap" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → must return 0 matches (not yet added). If 1+ → already patched, skip.

**Change A — insert swap block after `firedAlertsB` useMemo:**

Replace:
```tsx
  const firedAlertsB = useMemo(
    () => alertsB.filter((a) => a.timestamp_ms <= floorTs),
    [alertsB, floorTs]
  );

  if (loading) {
```
With:
```tsx
  const firedAlertsB = useMemo(
    () => alertsB.filter((a) => a.timestamp_ms <= floorTs),
    [alertsB, floorTs]
  );

  // Swap so higher score is always on the right column
  const scoreA = sessionA?.score_total ?? null;
  const scoreB = sessionB?.score_total ?? null;
  const swap = scoreA !== null && scoreB !== null && scoreA > scoreB;
  const leftId = swap ? sessionIdB : sessionIdA;
  const rightId = swap ? sessionIdA : sessionIdB;
  const leftSession = swap ? sessionB : sessionA;
  const rightSession = swap ? sessionA : sessionB;
  const leftAlerts = swap ? alertsB : alertsA;
  const rightAlerts = swap ? alertsA : alertsB;
  const leftAlertsError = swap ? alertsErrorB : alertsErrorA;
  const rightAlertsError = swap ? alertsErrorA : alertsErrorB;
  const leftScore = swap ? scoreB : scoreA;
  const rightScore = swap ? scoreA : scoreB;
  const leftFlash = swap ? columnBCriticalFlash : columnACriticalFlash;
  const rightFlash = swap ? columnACriticalFlash : columnBCriticalFlash;

  if (loading) {
```

**Change B — update 3D views: replace session A/B with left/right + add score badges:**

Replace:
```tsx
        <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <TorchWithHeatmap3D
                  angle={getFrameAtTimestamp(sessionA.frames, currentTimestamp)?.angle_degrees ?? 45}
                  temp={extractCenterTemperatureWithCarryForward(sessionA.frames, currentTimestamp)}
                  label={`Session A (${sessionIdA})`}
                  labelPosition="outside"
                  frames={frameDataA.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
              <div>
                <TorchWithHeatmap3D
                  angle={getFrameAtTimestamp(sessionB.frames, currentTimestamp)?.angle_degrees ?? 45}
                  temp={extractCenterTemperatureWithCarryForward(sessionB.frames, currentTimestamp)}
                  label={`Session B (${sessionIdB})`}
                  labelPosition="outside"
                  frames={frameDataB.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
            </div>
```
With:
```tsx
        <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <div className="flex items-center justify-between mb-2 px-1">
                  <span className="font-mono text-xs text-zinc-400 truncate">{leftId}</span>
                  {leftScore != null && (
                    <span className="font-mono text-sm font-bold text-zinc-200 ml-2 shrink-0">{Math.round(leftScore)}</span>
                  )}
                </div>
                <TorchWithHeatmap3D
                  angle={getFrameAtTimestamp((leftSession?.frames ?? []), currentTimestamp)?.angle_degrees ?? 45}
                  temp={extractCenterTemperatureWithCarryForward((leftSession?.frames ?? []), currentTimestamp)}
                  label={leftId}
                  labelPosition="outside"
                  frames={swap ? frameDataB.thermal_frames : frameDataA.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2 px-1">
                  <span className="font-mono text-xs text-zinc-400 truncate">{rightId}</span>
                  {rightScore != null && (
                    <span className="font-mono text-sm font-bold text-zinc-200 ml-2 shrink-0">{Math.round(rightScore)}</span>
                  )}
                </div>
                <TorchWithHeatmap3D
                  angle={getFrameAtTimestamp((rightSession?.frames ?? []), currentTimestamp)?.angle_degrees ?? 45}
                  temp={extractCenterTemperatureWithCarryForward((rightSession?.frames ?? []), currentTimestamp)}
                  label={rightId}
                  labelPosition="outside"
                  frames={swap ? frameDataA.thermal_frames : frameDataB.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
            </div>
```

**Change C — alert feed column headers (Session A/B count labels):**

Replace:
```tsx
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              Session A: {alertsErrorA != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${firedAlertsA.length} alerts`
              )}
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              Session B: {alertsErrorB != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${firedAlertsB.length} alerts`
              )}
            </div>
```
With:
```tsx
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              {leftId}: {leftAlertsError != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${(swap ? firedAlertsB : firedAlertsA).length} alerts`
              )}
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              {rightId}: {rightAlertsError != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${(swap ? firedAlertsA : firedAlertsB).length} alerts`
              )}
            </div>
```

**Change D — alert feed column containers (flash + AlertFeedColumn props):**

Replace:
```tsx
            <div
              className={`rounded-lg border p-4 transition-all ${
                columnACriticalFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={alertsA}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={alertsErrorA}
                label="Session A"
              />
            </div>
            <div
              className={`rounded-lg border p-4 transition-all ${
                columnBCriticalFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={alertsB}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={alertsErrorB}
                label="Session B"
              />
            </div>
```
With:
```tsx
            <div
              className={`rounded-lg border p-4 transition-all ${
                leftFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={leftAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={leftAlertsError}
                label={leftId}
              />
            </div>
            <div
              className={`rounded-lg border p-4 transition-all ${
                rightFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={rightAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={rightAlertsError}
                label={rightId}
              />
            </div>
```

**Change E — update tests: fix the two label assertions**

In `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx`:

Replace:
```tsx
    expect(labels).toContain(`Session A (${COMPARE_SESSION_ID_A})`);
```
With:
```tsx
    expect(labels).toContain(COMPARE_SESSION_ID_A);
```

Replace:
```tsx
    expect(labels).toContain(`Session B (${COMPARE_SESSION_ID_B})`);
```
With:
```tsx
    expect(labels).toContain(COMPARE_SESSION_ID_B);
```

Note: both `SESSION_A` and `SESSION_B` mocks have no `score_total`, so `swap = false`, `leftId = sessionIdA = COMPARE_SESSION_ID_A`, and `rightId = sessionIdB = COMPARE_SESSION_ID_B`. The tests still cover the no-swap path correctly.

**Git Checkpoint:**
```bash
git add "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx" \
        "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx"
git commit -m "feat: compare page — score badges + swap columns so higher score is always right"
```

**✓ Verification:**

**Type:** Unit (tests) + Integration (grep) + E2E (browser)

1. Run tests:
   ```bash
   cd my-app && npx jest "compare/\[sessionIdA\]/\[sessionIdB\]/page.test.tsx" --no-coverage
   ```
   → must show **5 passed, 0 failed**.

2. Confirm old raw session references gone from render:
   `grep -n "columnACriticalFlash\|columnBCriticalFlash\|alertsErrorA\|alertsErrorB\|\"Session A\"\|\"Session B\"" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → must return **0 matches** (state declarations are fine — only render-site uses must be gone).

   Note: `columnACriticalFlash` and `columnBCriticalFlash` still appear in state declarations and the `useEffect` — that is correct and expected. The grep above will match those lines. Refine the check to just render sites:
   `grep -n "\"Session A\"\|\"Session B\"\|alertsErrorA\|alertsErrorB" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → must return 0 matches.

3. Confirm score badges added:
   `grep -n "leftScore\|rightScore" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → must return matches.

4. E2E: Navigate to `/compare/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`.
   - If sessions have `score_total`, higher score is on right with score badge visible
   - If sessions have null `score_total`, no swap (URL order preserved), no score badge — sessions display in URL order

**Fail:**
- Tests fail with `expect(labels).toContain(...)` mismatch → label format changed unexpectedly — re-read page.tsx to confirm `leftId = sessionIdA` when no swap
- `grep` still shows `"Session A"` or `"Session B"` → one of Changes C/D was not applied — re-read file and re-apply

---

## Step 3: TypeScript check — confirm no new type errors

**Idempotent:** Yes — read-only check.

**Files checked:** Both pages.

```bash
cd my-app && npx tsc --noEmit 2>&1 | grep -E "demo/\[sessionIdA\]|compare/\[sessionIdA\]" | head -20
```

**Pass:** 0 lines output (no type errors in either page).

**Fail:**
- `Property 'frames' does not exist on type 'null'` → `leftSession?.frames` access on null session — add null guard: `(leftSession?.frames ?? [])`
- `Type 'number | null' is not assignable to type 'number'` → `leftScore` passed to `WQIScore value=` which expects `number | null | undefined` — check `WQIScore` prop type in demo page (it accepts `number | null | undefined`)

**Git Checkpoint:** No separate commit. TypeScript errors must be fixed before committing Step 1 or Step 2. Fold TypeScript fixes into the relevant step's commit.

---

## Regression Guard

| System | Pre-change | Post-change check |
|---|---|---|
| Compare page tests (5 tests) | All 5 passing | `npx jest compare` → 5/5 passing |
| Demo page 3D rendering | Sessions load and display | Navigate to `/demo/...` → both circles render |
| Simulator "View 3D Comparison" link | Hardcoded to `/demo/expert/novice` | Unchanged — Step 1/2 don't touch simulator page |

---

## Success Criteria

| Feature | Target | Verification |
|---|---|---|
| Demo WQI scores always visible | Never shows `--` | Open `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` → both WQI scores show numbers |
| Higher score on right (demo) | Expert (higher) on right, novice (lower) on left | Expert session ID appears under right (green) WQI score |
| Compare score badges | Score number above each 3D view when `score_total` non-null | Run analysis on sessions, then compare → score badge visible |
| Higher score on right (compare) | Same ordering rule | Compare expert vs novice → expert column is on right |
| Tests pass | 5/5 | `npx jest compare` → green |
| TypeScript | No new errors | `npx tsc --noEmit` → 0 errors in modified files |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch multiple steps into one git commit.**
⚠️ **Step 3 (TypeScript check) must pass before marking Steps 1 or 2 done.**
⚠️ **The `summaryText` computation in compare page still references "Session A"/"Session B" as hardcoded strings — this is informational text only and is intentionally left unchanged (out of scope).**
