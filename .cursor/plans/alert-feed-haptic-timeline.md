# Feature Implementation Plan: Alert Feed Pop-In Pattern

**Overall Progress:** `100%`

## TLDR

Alerts pop into the feed the moment `currentTimestamp >= alert.timestamp_ms`. Each fired alert has three states: **Active** (elapsed < 2s — live counter ticking), **Corrected** (dot goes green, counter stops), **Uncorrected** (elapsed ≥ 2s, card dims, ✗ footer). All time is session time derived from `currentTimestamp` — scrubbing backwards rewinds the counter. Mock data only; no real-time infrastructure needed. Demo page first (Steps 1a, 1b); compare page follows (Step 2).

---

## Critical Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| Render model | **Pop-in** — filter to `timestamp_ms <= currentTimestamp` | No pre-rendering. Alert appears the moment its timestamp passes. |
| Sort order | **Descending** (b.timestamp_ms - a.timestamp_ms) | Newest alert at top; no scroll needed. |
| Active window | **2s session time** | elapsed = (currentTimestamp - alert.timestamp_ms) / 1000. Scrub-reversible. |
| Corrected threshold | `elapsed >= alert.corrected_in_seconds` | No wall-clock involved. Derived entirely from currentTimestamp. |
| Uncorrected threshold | `elapsed >= 2 && !correctedNow` | Card dims; ✗ footer. Simple, no edge cases for mock data. |
| Key prop | `alert.frame_index` | Unique per alert. Never use timestamp_ms or rule_triggered (duplicate risk). |
| Count badge | `alertsX.filter(a => a.timestamp_ms <= floorTs).length` | Fired count only. |

---

## Per-Card State Machine

Every fired alert card derives its state from `currentTimestamp`. No local React state needed.

```ts
const elapsed = (currentTimestamp - alert.timestamp_ms) / 1000; // session seconds

const correctedNow =
  alert.corrected === true &&
  alert.corrected_in_seconds != null &&
  elapsed >= alert.corrected_in_seconds;

const uncorrected = !correctedNow && elapsed >= 2;

// active = fired && !correctedNow && !uncorrected
// i.e. elapsed < 2 and not yet corrected
```

**State → Visual mapping:**

| State | Dot color | Counter | Footer | Opacity |
|-------|-----------|---------|--------|---------|
| Active | amber (pulsing) | `+{elapsed.toFixed(1)}s` ticking | — | 1 |
| Corrected | green | stopped at corrected_in_seconds | `✓ corrected in X.Xs` | 1 |
| Uncorrected | red dim | — | `✗ not corrected` | 0.5 |

---

## correctedNow — Authoritative Definition

```ts
const elapsed = currentTimestamp != null
  ? (currentTimestamp - alert.timestamp_ms) / 1000
  : 0;

const correctedNow =
  alert.corrected === true &&
  alert.corrected_in_seconds != null &&  // null guard — never fallback to 0
  elapsed >= alert.corrected_in_seconds;

const uncorrected = !correctedNow && elapsed >= 2;
```

**Critical:** `corrected_in_seconds ?? 0` is WRONG — if null, sec=0 makes correctedNow true immediately on pop-in. Always null-guard with `!= null` and bail.

---

## Agent Failure Protocol

1. Verification fails → read full error.
2. Cause clear → ONE fix → re-run same command.
3. Still failing → STOP. Output modified files, command, error, fix, state, why blocked.
4. No second fix without human instruction.
5. Never modify files not named in the step.

---

## Pre-Flight — Run Before Any Code Changes

**1. AlertPayload type:**
```bash
grep -n "export interface AlertPayload" my-app/src/lib/api.ts
```
Expected: exactly 1 match. Paste the full interface definition.

**2. C tokens — confirm exact keys used by AlertFeedColumn:**
```bash
grep -n "^const C\b\|^  [a-zA-Z]" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx | head -40
```
From the output, identify and record the exact key names for: amber/warning color, dim text color, green/success color, red/error color, border color. AlertFeedColumn will use ONLY these five. No guessing.

**3. visibleAlertsX full audit:**
```bash
grep -rn "visibleAlertsA\|visibleAlertsB" my-app/src/app/
```
Categorise every match: (a) useMemo definition, (b) display map, (c) count badge, (d) flash logic, (e) prevVisibleIds, (f) other. Deletion authorised only when every match is categorised as a–e. If any match is (f) → STOP.

**4. Compare — seek handler and timestamp variable names:**
```bash
grep -n "setCurrentTimestamp\|setIsPlaying\|floorTs\|firstTimestamp" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx | head -10
```
Confirm: `floorTs = currentTimestamp ?? firstTimestamp ?? 0` exists. Record exact seek handler names. Component invocation must use these exact names.

**5. Compare — full flash useEffect:**
```bash
grep -n "visibleAlertsA\|visibleAlertsB\|prevVisibleIds\|columnACriticalFlash\|columnBCriticalFlash" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
```
Paste every matching line. List each line number that must change from visibleAlerts → firedAlerts.

**6. Build baseline:**
```bash
cd my-app && npm run build 2>&1 | tail -5
```
Record exit code. Must be 0 before proceeding.

**Baseline Snapshot (agent fills):**
```
Build exit code: ____
AlertPayload fields: ____
C token for amber/warning: ____
C token for dim text: ____
C token for green/success: ____
C token for red/error: ____
C token for border: ____
floorTs definition: ____
Seek handler: ____
visibleAlertsA usages (line numbers + category): ____
visibleAlertsB usages (line numbers + category): ____
Flash useEffect lines to change: ____
```

---

## Step 1a: Demo — Add AlertFeedColumn 🟥

**Idempotent:** Yes — adds a new function only.

**Pre-Read Gate:**
```bash
grep -n "function AlertCard" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
```
Record exact line number. Insert AlertFeedColumn immediately before the line that reads `function AlertCard(` — not before JSDoc comments or blank lines above it.

**Substitute C tokens:** Before inserting, replace the five placeholder tokens below with the exact C key names recorded in Pre-Flight step 2:
- `C.AMBER` → C token for amber/warning
- `C.DIMTEXT` → C token for dim text
- `C.GREEN` → C token for green/success
- `C.RED` → C token for red/error
- `C.BORDER` → C token for border

**Insert this component (with substituted tokens) before `function AlertCard(`:**

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
      <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.AMBER }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          fontSize: 7,
          fontWeight: 600,
          letterSpacing: '0.28em',
          color: C.DIMTEXT,
          textTransform: 'uppercase',
          marginBottom: 8,
        }}
      >
        {label}
      </div>

      {firedAlerts.length === 0 ? (
        <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.DIMTEXT }}>
          No alerts yet
        </div>
      ) : (
        firedAlerts.map((alert) => {
          const elapsed =
            currentTimestamp != null
              ? (currentTimestamp - alert.timestamp_ms) / 1000
              : 0;

          const correctedNow =
            alert.corrected === true &&
            alert.corrected_in_seconds != null &&
            elapsed >= alert.corrected_in_seconds;

          const uncorrected = !correctedNow && elapsed >= 2;

          // active = fired && !correctedNow && !uncorrected
          const dotColor = correctedNow
            ? C.GREEN
            : uncorrected
            ? C.RED
            : C.AMBER;

          const cardOpacity = uncorrected ? 0.5 : 1;

          return (
            <button
              key={alert.frame_index}
              type="button"
              onClick={() => onSeek(alert.timestamp_ms)}
              style={{
                width: '100%',
                textAlign: 'left',
                background: 'none',
                border: 'none',
                borderBottom: `1px solid ${C.BORDER}`,
                padding: '8px 0',
                cursor: 'pointer',
                opacity: cardOpacity,
                transition: 'opacity 0.4s ease',
                display: 'flex',
                gap: 10,
              }}
            >
              {/* Pulse dot */}
              <div style={{ flexShrink: 0, paddingTop: 3 }}>
                <div
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: dotColor,
                    transition: 'background 0.3s ease',
                  }}
                />
              </div>

              <div style={{ flex: 1 }}>
                {/* Rule label + live counter */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONT_LABEL,
                      fontSize: 9,
                      fontWeight: 600,
                      letterSpacing: '0.16em',
                      textTransform: 'uppercase',
                      color: correctedNow ? C.GREEN : uncorrected ? C.RED : C.AMBER,
                    }}
                  >
                    {getRuleLabel(alert.rule_triggered)}
                  </span>

                  {/* Counter: ticking when active, frozen when corrected, hidden when uncorrected */}
                  {!uncorrected && (
                    <span
                      style={{
                        fontFamily: FONT_DATA,
                        fontSize: 8,
                        color: correctedNow ? C.GREEN : C.DIMTEXT,
                      }}
                    >
                      {correctedNow
                        ? `+${alert.corrected_in_seconds!.toFixed(1)}s`
                        : `+${elapsed.toFixed(1)}s`}
                    </span>
                  )}
                </div>

                {/* Message */}
                <div
                  style={{
                    fontFamily: FONT_DATA,
                    fontSize: 7.5,
                    color: C.DIMTEXT,
                    marginTop: 2,
                  }}
                >
                  {alert.message}
                </div>

                {/* State footer */}
                <div style={{ marginTop: 3 }}>
                  {correctedNow && (
                    <span
                      style={{
                        fontFamily: FONT_LABEL,
                        fontSize: 7.5,
                        letterSpacing: '0.14em',
                        color: C.GREEN,
                        textTransform: 'uppercase',
                      }}
                    >
                      ✓ corrected in {alert.corrected_in_seconds!.toFixed(1)}s
                    </span>
                  )}
                  {uncorrected && (
                    <span
                      style={{
                        fontFamily: FONT_DATA,
                        fontSize: 7.5,
                        color: C.RED,
                      }}
                    >
                      ✗ not corrected
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}
```

**✓ Verification:**
```bash
cd my-app && npx tsc --noEmit 2>&1 | grep -c "error TS"
```
Expected: `0`. If nonzero, read full output, make one fix, re-run. Do not proceed to 1b until this passes.

---

## Step 1b: Demo — Replace grid, update badge, remove visibleAlerts 🟥

**Idempotent:** No — destructive removal of visibleAlertsA/B.

**Pre-Read Gate:**
```bash
grep -n "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
```
Every match must be categorised as one of: useMemo definition (delete), count badge (replace), display map (replace). If any match is uncategorised → STOP.

**Anchor uniqueness — run before each edit:**
```bash
grep -c "visibleAlertsA\.map" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 1
grep -c "visibleAlertsB\.map" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 1
```

**Changes (in order):**

**1. Add firedCountA / firedCountB** (add immediately after the existing `floorTs` line):
```ts
const firedCountA = useMemo(
  () => alertsA.filter((a) => a.timestamp_ms <= floorTs).length,
  [alertsA, floorTs]
);
const firedCountB = useMemo(
  () => alertsB.filter((a) => a.timestamp_ms <= floorTs).length,
  [alertsB, floorTs]
);
```

**2. Replace count badges:**
- `visibleAlertsA.length` → `firedCountA`
- `visibleAlertsB.length` → `firedCountB`

**3. Remove visibleAlertsA and visibleAlertsB useMemo blocks** — delete both blocks entirely.

**4. Replace column inner content — keep outer wrapper div:**
The outer wrapper div (with `borderRight`, `padding`, `overflowY`) stays untouched. Replace only its children with:
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
Same for Session B. Do not touch the wrapper div's style props.

**5. AlertCard removal — required grep:**
```bash
grep -n "AlertCard" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
```
If results contain only the `function AlertCard(` definition line and zero invocations → delete the entire AlertCard function block. If any invocation line appears → leave it.

**✓ Verification:**
```bash
# TypeScript
cd my-app && npx tsc --noEmit 2>&1 | grep -c "error TS"
# Expected: 0

# visibleAlerts fully removed
grep -c "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 0
```

**Runtime checks:**
- At t=0: feed shows "No alerts yet"
- Advance past first alert: card pops in, dot amber, counter ticking `+0.0s +0.1s…`
- Advance past `alert.timestamp_ms + 2000`: card dims to 0.5, footer "✗ not corrected"
- Advance past `alert.timestamp_ms + corrected_in_seconds * 1000` on a corrected alert: dot green, counter frozen, footer "✓ corrected in X.Xs"
- Click card: playback seeks to that alert's timestamp

**Git Checkpoint:**
```bash
git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
git commit -m "step 1b: wire AlertFeedColumn into demo, remove visibleAlerts"
```

---

## Step 2: Compare — Same pattern, Tailwind 🟥

**Idempotent:** Yes.

**Pre-Read Gate:**
```bash
# Confirm seek handler names
grep -n "setCurrentTimestamp\|setIsPlaying\|floorTs" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx | head -10

# Full flash useEffect — paste output before editing
grep -n "visibleAlertsA\|visibleAlertsB\|prevVisibleIds\|columnACriticalFlash\|columnBCriticalFlash" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx

# AlertCard location
grep -n "function AlertCard" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
```

**Anchor uniqueness:**
```bash
grep -c "visibleAlertsA\.map" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 1
grep -c "visibleAlertsB\.map" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 1
```

**Changes (in order):**

**1. Add firedAlertsA / firedAlertsB** (for flash + badge only — not for display):
```ts
const firedAlertsA = useMemo(
  () => alertsA.filter((a) => a.timestamp_ms <= floorTs),
  [alertsA, floorTs]
);
const firedAlertsB = useMemo(
  () => alertsB.filter((a) => a.timestamp_ms <= floorTs),
  [alertsB, floorTs]
);
```

**2. Flash useEffect:** Replace every `visibleAlertsA` → `firedAlertsA` and `visibleAlertsB` → `firedAlertsB` inside the flash useEffect. Update the dependency array too. Line numbers to change are those listed in pre-flight step 5.

**3. Remove visibleAlertsA / visibleAlertsB useMemo blocks.**

**4. Count badges:** `visibleAlertsA.length` → `firedAlertsA.length`, same for B.

**5. Add Tailwind AlertFeedColumn before `function AlertCard(`:**
Same three-state logic as demo. Tailwind version:

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

  if (error) return <div className="p-2 text-xs text-amber-500">{error}</div>;

  return (
    <div className="flex flex-col">
      <div className="text-[7px] font-semibold tracking-[0.28em] uppercase text-zinc-500 mb-2">
        {label}
      </div>

      {firedAlerts.length === 0 ? (
        <div className="text-[9px] text-zinc-500">No alerts yet</div>
      ) : (
        firedAlerts.map((alert) => {
          const elapsed =
            currentTimestamp != null
              ? (currentTimestamp - alert.timestamp_ms) / 1000
              : 0;

          const correctedNow =
            alert.corrected === true &&
            alert.corrected_in_seconds != null &&
            elapsed >= alert.corrected_in_seconds;

          const uncorrected = !correctedNow && elapsed >= 2;

          const dotClass = correctedNow
            ? 'bg-green-500'
            : uncorrected
            ? 'bg-red-500 opacity-50'
            : 'bg-amber-500';

          return (
            <button
              key={alert.frame_index}
              type="button"
              onClick={() => onSeek(alert.timestamp_ms)}
              className={`w-full text-left bg-transparent border-0 border-b border-zinc-800 py-2 cursor-pointer flex gap-2.5 transition-opacity duration-400 ${uncorrected ? 'opacity-50' : 'opacity-100'}`}
            >
              {/* Dot */}
              <div className="shrink-0 pt-0.5">
                <div className={`w-[7px] h-[7px] rounded-full transition-colors duration-300 ${dotClass}`} />
              </div>

              <div className="flex-1">
                {/* Rule + counter */}
                <div className="flex justify-between items-baseline">
                  <span className={`text-[9px] font-semibold tracking-[0.16em] uppercase ${correctedNow ? 'text-green-500' : uncorrected ? 'text-red-500' : 'text-amber-500'}`}>
                    {getRuleLabel(alert.rule_triggered)}
                  </span>
                  {!uncorrected && (
                    <span className={`text-[8px] ${correctedNow ? 'text-green-500' : 'text-zinc-500'}`}>
                      {correctedNow
                        ? `+${alert.corrected_in_seconds!.toFixed(1)}s`
                        : `+${elapsed.toFixed(1)}s`}
                    </span>
                  )}
                </div>

                {/* Message */}
                <div className="text-[7.5px] text-zinc-500 mt-0.5">{alert.message}</div>

                {/* Footer */}
                <div className="mt-0.5">
                  {correctedNow && (
                    <span className="text-[7.5px] tracking-[0.14em] uppercase text-green-500">
                      ✓ corrected in {alert.corrected_in_seconds!.toFixed(1)}s
                    </span>
                  )}
                  {uncorrected && (
                    <span className="text-[7.5px] text-red-500">✗ not corrected</span>
                  )}
                </div>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}
```

**6. Replace column display content** — keep outer wrapper div, replace inner children only:
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
Use exact variable names confirmed in pre-read gate. Same for B.

**7. AlertCard removal:**
```bash
grep -n "AlertCard" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
```
If only the definition line remains (zero invocations) → delete the function block. Document the line range deleted.

**✓ Verification:**
```bash
# TypeScript
cd my-app && npx tsc --noEmit 2>&1 | grep -c "error TS"
# Expected: 0

# visibleAlerts fully removed
grep -c "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 0

# firedAlerts never used for display iteration
grep -c "firedAlertsA\.map\|firedAlertsB\.map" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
# Expected: 0
```

**Runtime checks:**
- Same three-state behavior as demo
- Critical column flash still triggers when a critical alert fires
- Scrub backwards: counter rewinds, uncorrected card un-dims if elapsed < 2s again

**Git Checkpoint:**
```bash
git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
git commit -m "step 2: compare page three-state alert feed, firedAlerts for flash and badge"
```

---

## Regression Guard

| Check | Command | Expected |
|-------|---------|----------|
| visibleAlerts removed (demo) | `grep -c "visibleAlertsA\|visibleAlertsB" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` | 0 |
| visibleAlerts removed (compare) | `grep -c "visibleAlertsA\|visibleAlertsB" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | 0 |
| firedAlerts not used for display map | `grep -c "firedAlertsA\.map\|firedAlertsB\.map" my-app/src/app/` | 0 |
| TypeScript | `cd my-app && npx tsc --noEmit 2>&1 \| grep -c "error TS"` | 0 |
| Scrub backwards | Manual: advance past uncorrected threshold, scrub back | Card un-dims, counter rewinds |
| Critical flash | Manual: advance past critical alert on compare | Column flash triggers |

---

## Success Criteria

- [ ] Card pops in the moment `currentTimestamp >= alert.timestamp_ms`
- [ ] Active state: amber dot, counter ticking `+0.0s…`
- [ ] Corrected state: green dot, counter frozen, "✓ corrected in X.Xs"
- [ ] Uncorrected state (elapsed ≥ 2s): red dim dot, opacity 0.5, "✗ not corrected"
- [ ] Scrub backwards: state machine rewinds correctly (uncorrected → active if elapsed < 2s)
- [ ] `corrected_in_seconds` null guard in place — no immediate green flash on pop-in
- [ ] key={alert.frame_index} on all cards
- [ ] visibleAlerts grep returns 0 in both files
- [ ] tsc passes
- [ ] Critical flash unaffected on compare page

---

⚠️ Do not proceed to Step 1b until Step 1a tsc check returns 0.
⚠️ Do not proceed to Step 2 until Step 1b runtime checks pass.
⚠️ Do not batch steps into one commit.
⚠️ If any pre-read gate grep returns an unexpected result → STOP and report before editing.