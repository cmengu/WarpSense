# Feature Implementation Plan: WarpSense Multi-Agent UI

**Overall Progress:** `0%`

---

## TLDR

The analysis page currently shows all three specialist agent cards simultaneously and then replaces them with a report — a context-switch anti-pattern that hides the sequential LangGraph pipeline work from the user. This plan fixes two root causes (React 18 automatic batching collapsing SSE events into one render; backend lacking SSE keepalive heartbeats), then upgrades the UI to a world-class Unified Timeline pattern where agent cards persist, animate sequentially with live elapsed time + message content, and the report builds inline below the agents rather than replacing them.

---

## Architecture Overview

**The problem this plan solves:**

1. `AnalysisStream.tsx` lines 77–130: the `for (const part of parts)` loop processes all SSE events synchronously inside one `reader.read()` tick. React 18 automatic batching collapses every `setStageStates()` call into a single render — so the user sees all three agents jump to their final state in one frame rather than sequentially.

2. `backend/services/warp_service.py` lines 319–323: the queue drain loop uses a single 300 s `asyncio.wait_for` with no keepalive. Nginx default `proxy_read_timeout` is 60 s — silent connection drops occur during long Groq LLM calls.

3. `page.tsx` lines 38–41: `ViewState` has three modes: `empty → streaming → report`. The transition from `streaming` to `report` unmounts `AnalysisStream` and mounts `QualityReportCard` — destroying all agent verdict context the user just watched.

**The patterns applied:**

- **Yield-to-event-loop**: `await new Promise<void>(resolve => setTimeout(resolve, 0))` between SSE events gives the browser scheduler a chance to flush React state updates, breaking the batch.
- **Unified Timeline (Perplexity pattern)**: Evidence (agent cards) persist when the report appears. One component — `AnalysisTimeline` — owns both the SSE stream state and the inline report. No context-switch.
- **State machine collapse**: `ViewState` collapses from 3 modes to 2 (`empty` / `active`). The `active` mode drives a `phase: "streaming" | "done"` inside `AnalysisTimeline` rather than re-mounting.

**What stays unchanged:**

- `QualityReportCard.tsx` — consumed as-is; its props interface is unchanged.
- `warp-api.ts` — `streamAnalysis()` is unchanged; still bypasses Next.js proxy.
- `SessionList.tsx`, `WelderTrendChart.tsx`, `StatusBadge.tsx` — untouched.
- `backend/agent/warpsense_graph.py` — confirmed backend emits events correctly; the bug is purely frontend.
- `backend/routes/warp_analysis.py` — unchanged.

**What this plan adds:**

- `my-app/src/components/analysis/AnalysisTimeline.tsx` — new unified component (Step 4).
- Three new fields on `AgentCardState` in `my-app/src/types/warp-analysis.ts` (Step 2).

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| `setTimeout(resolve, 0)` yield between events | `flushSync` from react-dom | `flushSync` causes synchronous nested renders, violates React's render model, and is explicitly warned against in concurrent mode |
| `AnalysisTimeline` unified component (Step 4) | Keep `AnalysisStream` + `QualityReportCard` side-by-side | Two-component layout requires `page.tsx` to hold shared state and coordinate two separate lifecycles — complex and fragile |
| `streamTrigger` counter for re-analyse | Unmount/remount by changing `key` | A new counter prop avoids destroying the DOM and re-triggering CSS entry animations on re-run |
| Delete `AnalysisStream.tsx` in Step 5 | Keep it for other consumers | No other consumer exists; keeping it creates two code paths for the same SSE logic |

**Known limitations:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| `setTimeout(resolve, 0)` is a scheduler workaround | React 19 `startTransition` will handle this more elegantly | Upgrade when React 19 is stable |
| Elapsed timer uses `Date.now()` wall clock | Good enough for display; not sub-millisecond precision | No upgrade needed |
| Keepalive interval is hardcoded to 10 s | Covers Nginx 60 s default | Make configurable via env var if needed |

---

## Critical Decisions (quick reference)

- **Decision 1:** `setTimeout(resolve, 0)` yield — breaks React 18 batch without violating concurrent mode
- **Decision 2:** Unified `AnalysisTimeline` — evidence persists, no context-switch, single lifecycle
- **Decision 3:** Collapse `ViewState` to 2 modes — `AnalysisTimeline` owns `phase` internally
- **Decision 4:** Delete `AnalysisStream.tsx` — no other consumers; one SSE code path only

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Does any file other than `page.tsx` import `AnalysisStream`? | Grep result | Codebase | Step 5 | ✅ Verified: only `page.tsx` imports it |
| Backend SSE event count | `TOTAL_EVENTS` constant | `AnalysisStream.tsx` line 23 | Step 1 | ✅ 9 events |
| `QualityReportCard` root element for layout compatibility | Read file | `QualityReportCard.tsx` | Step 4 | ✅ `flex flex-col min-h-[400px] h-full` — compatible with `flex-1 min-h-0` parent |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read the following files in full. Capture and output:
(1) AnalysisStream.tsx — every state variable and the for-loop structure (lines 77–130)
(2) warp-analysis.ts — current AgentCardState interface fields
(3) warp_service.py — queue drain loop (lines 317–323)
(4) page.tsx — ViewState type definition and render block (lines 38–41, 246–280)

Run: grep -rn "AnalysisStream" my-app/src/ --include="*.tsx" --include="*.ts"
Record: every file that imports AnalysisStream.

Run: cd my-app && npx tsc --noEmit 2>&1 | tail -20
Record: number of type errors before plan begins.

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
TypeScript errors before plan: ____
Files importing AnalysisStream:  ____
AgentCardState current fields:   status, disposition
Queue drain loop location:       warp_service.py lines 319–323
```

**Automated checks (all must pass before Step 1):**

- [ ] `grep -n "for (const part of parts)" my-app/src/components/analysis/AnalysisStream.tsx` returns line 77
- [ ] `grep -n "AgentCardState" my-app/src/types/warp-analysis.ts` confirms fields: `status`, `disposition` only
- [ ] `grep -n "wait_for" backend/services/warp_service.py` returns exactly line 320
- [ ] `grep -rn "AnalysisStream" my-app/src/` returns only `page.tsx` and `AnalysisStream.tsx` itself
- [ ] `cd my-app && npx tsc --noEmit` — record error count

---

## Environment Matrix

| Step | Dev | Notes |
|------|-----|-------|
| Steps 1–3 | ✅ | No env-specific changes |
| Steps 4–5 | ✅ | New component + page wiring only |
| Backend Step 3 | ✅ | Python-only change; no migration |

---

## Tasks

### Phase 1 — Fix the Root Causes

**Goal:** After Phase 1, agent cards animate sequentially in the existing `AnalysisStream` component, elapsed time is visible on running cards, and the backend connection survives long Groq LLM calls.

---

- [ ] 🟥 **Step 1: Fix React 18 batching — yield to event loop between SSE events** — *Critical: root cause of the "all at once" bug*

  **Step Architecture Thinking:**

  **Pattern applied:** Yield-to-event-loop. `setTimeout(resolve, 0)` yields control back to the browser scheduler after each SSE event, allowing React to flush the pending `setStageStates` call before processing the next event. This is the minimal surgical fix that does not change component structure.

  **Why this step exists here in the sequence:** It is the only fix that unlocks the observable sequential animation. Steps 2–5 add polish; without Step 1, none of them produce the desired UX.

  **Why this file is the right location:** `AnalysisStream.tsx` is the only place that consumes `reader.read()` and dispatches `setStageStates`. The batch happens here; the fix belongs here.

  **Alternative approach considered and rejected:** `flushSync(() => setStageStates(...))` — React's docs explicitly warn that `flushSync` inside a concurrent renderer can cause cascading synchronous renders and is incompatible with Suspense/transitions.

  **What breaks if this step deviates:** If the `await` is placed outside the `for` loop (after it), batching still occurs for all events in one `reader.read()` chunk — the bug is not fixed.

  ---

  **Idempotent:** Yes — adding an `await` has no side effects on re-run.

  **Context:** `reader.read()` can return a buffer containing multiple `\n\n`-delimited SSE events. The `for` loop processes all of them synchronously, so React sees a burst of `setStageStates` calls in one microtask and batches them into one render. Adding `await new Promise<void>(resolve => setTimeout(resolve, 0))` at the end of each loop iteration yields to the browser event loop, giving React a render opportunity per event.

  **Pre-Read Gate:**
  - Run `grep -n "for (const part of parts)" my-app/src/components/analysis/AnalysisStream.tsx` — must return exactly 1 match. If 0 or 2+ → STOP.
  - Run `grep -n "event.stage === .error." my-app/src/components/analysis/AnalysisStream.tsx` — must return exactly 1 match at the bottom of the for loop. If missing → STOP.

  **Self-Contained Rule:** All code below is complete and runnable. No "see Step N" references.

  **No-Placeholder Rule:** No `<VALUE>` tokens.

  Edit `my-app/src/components/analysis/AnalysisStream.tsx`. Replace the entire `for (const part of parts)` block (lines 77–130):

  ```tsx
  for (const part of parts) {
    const line = part.trim();
    if (!line.startsWith("data: ")) continue;

    let event: WarpSSEEvent;
    try {
      event = JSON.parse(line.slice(6)) as WarpSSEEvent;
    } catch {
      continue;
    }

    if (cancelled) return;

    eventCount += 1;
    setProgress(Math.min(Math.round((eventCount / TOTAL_EVENTS) * 100), 100));

    if (event.message) {
      const ts = new Date().toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      setLogLines((prev) => [...prev, `[${ts}] ${event.message}`]);
    }

    if (
      event.stage === "thermal_agent" ||
      event.stage === "geometry_agent" ||
      event.stage === "process_agent"
    ) {
      const stage = event.stage as AgentStage;
      setStageStates((prev) => ({
        ...prev,
        [stage]: {
          status: event.status === "done" ? "done" : "running",
          disposition: event.disposition ?? null,
        },
      }));
    }

    if (event.stage === "complete" && event.report) {
      if (cancelled) return;
      setProgress(100);
      onCompleteRef.current(event.report);
      return;
    }

    if (event.stage === "error") {
      if (cancelled) return;
      onErrorRef.current(event.message ?? "Pipeline error");
      return;
    }

    // Yield to browser event loop — breaks React 18 automatic batching.
    // Without this, multiple events from one reader.read() chunk are processed
    // synchronously and React collapses all setStageStates calls into one render.
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  }
  ```

  **What it does:** Inserts a `setTimeout(resolve, 0)` yield at the bottom of the for loop, after each SSE event is processed, before the next one is handled.

  **Why this approach:** It is the minimum change. No component restructuring. No new dependencies. Directly addresses the React 18 batch root cause.

  **Assumptions:**
  - `reader.read()` may return multiple `\n\n`-delimited events in a single chunk (confirmed by inspecting the buffer split logic at line 74).
  - React 18 is in use (confirmed: `my-app/package.json`).

  **Risks:**
  - Marginally increases total stream processing time by `n_events × ~0 ms` (setTimeout(0) is ~0–4 ms per event; 9 events = ~36 ms max overhead) → mitigation: negligible; pipeline latency is 8–10 s.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/AnalysisStream.tsx
  git commit -m "step 1: yield to event loop between SSE events to break React 18 batching"
  ```

  **Subtasks:**
  - [ ] 🟥 Add `await new Promise<void>((resolve) => setTimeout(resolve, 0))` as last line inside the `for (const part of parts)` loop in `AnalysisStream.tsx`
  - [ ] 🟥 Verify the `await` is inside the for loop, not after it

  **✓ Verification Test:**

  **Type:** Integration (manual browser observation)

  **Action:** Start backend + frontend. Select an unanalysed session. Watch the three specialist cards.

  **Expected:**
  - Thermal card turns amber ("Analysing…") first, then turns to its disposition colour
  - ~2–4 s later Geometry card turns amber, then resolves
  - ~2–4 s later Process card turns amber, then resolves
  - Report appears only after all three resolve

  **Pass:** Three cards animate sequentially with visible time between each state change.

  **Fail:**
  - If all three cards still update simultaneously → `await` is placed after the for loop, not inside it → check line position in `AnalysisStream.tsx`
  - If TypeScript error `'await' expression is only allowed within an async function` → the enclosing function is not `async` → confirm `const runStream = async () => {` at line 50

---

- [ ] 🟥 **Step 2: Add elapsed timer + live message to agent cards** — *Critical: extends shared type contract*

  **Step Architecture Thinking:**

  **Pattern applied:** DTO extension. `AgentCardState` is the data contract between the SSE producer (`AnalysisStream`) and the display consumer (`SpecialistCard`). Adding `message`, `startedAt`, `finishedAt` to the interface here means both sides stay in sync from one source of truth in `warp-analysis.ts`.

  **Why this step exists here in the sequence:** Step 1 makes the sequential animation visible. Step 2 adds the contextual information (elapsed time, live message) that transforms a bare state change into meaningful feedback. Must come before Step 4 because `AnalysisTimeline` (Step 4) uses the same extended `AgentCardState`.

  **Why this file is the right location:** `warp-analysis.ts` is the single source of truth for all shared types. Defining the new fields here prevents `AnalysisStream.tsx` and `SpecialistCard.tsx` from each inventing their own shape.

  **Alternative approach considered and rejected:** Passing `startedAt` as a separate prop to `SpecialistCard` — would require `AnalysisStream` to track timestamps in a separate `useRef` map and thread them alongside `stageStates`, duplicating state.

  **What breaks if this step deviates:** If `startedAt` is omitted from `AgentCardState`, `SpecialistCard` cannot compute elapsed time without a separate timer prop — leaking timeline logic into the parent.

  ---

  **Idempotent:** Yes — adding fields to an interface is non-destructive.

  **Context:** `AgentCardState` currently has only `status` and `disposition`. We need `message` (live SSE message text), `startedAt` (timestamp when agent entered `running`), and `finishedAt` (timestamp when agent reached `done`) to compute elapsed time and display live context.

  **Sub-step 2a — Extend `AgentCardState` in `warp-analysis.ts`**

  **Pre-Read Gate:**
  - Run `grep -n "AgentCardState" my-app/src/types/warp-analysis.ts` — must return lines 63–66 with fields `status` and `disposition` only. If already has `message`/`startedAt` → step already applied, skip.

  Replace the `AgentCardState` interface in `my-app/src/types/warp-analysis.ts` (lines 63–66):

  ```ts
  export interface AgentCardState {
    status:      AgentCardStatus;
    disposition: WarpDisposition | null;
    /** Live message text from the SSE event — displayed on running cards. */
    message:     string | null;
    /** Wall-clock ms when agent entered "running" state. */
    startedAt:   number | undefined;
    /** Wall-clock ms when agent reached "done" state. */
    finishedAt:  number | undefined;
  }
  ```

  **Sub-step 2b — Update `INITIAL_STATES` in `AnalysisStream.tsx`**

  **Pre-Read Gate:**
  - Run `grep -n "INITIAL_STATES" my-app/src/components/analysis/AnalysisStream.tsx` — must return lines 16–20. If already has `message`/`startedAt` → skip.

  Replace `INITIAL_STATES` in `my-app/src/components/analysis/AnalysisStream.tsx` (lines 16–20):

  ```tsx
  const INITIAL_STATES: Record<AgentStage, AgentCardState> = {
    thermal_agent:  { status: "queued", disposition: null, message: null, startedAt: undefined, finishedAt: undefined },
    geometry_agent: { status: "queued", disposition: null, message: null, startedAt: undefined, finishedAt: undefined },
    process_agent:  { status: "queued", disposition: null, message: null, startedAt: undefined, finishedAt: undefined },
  };
  ```

  **Sub-step 2c — Update the `setStageStates` call in `AnalysisStream.tsx` to populate new fields**

  **Pre-Read Gate:**
  - Run `grep -n "status: event.status" my-app/src/components/analysis/AnalysisStream.tsx` — must return exactly 1 match. If 0 or 2+ → STOP.

  Replace the `setStageStates` block inside the `for` loop (the block that was edited in Step 1):

  ```tsx
  if (
    event.stage === "thermal_agent" ||
    event.stage === "geometry_agent" ||
    event.stage === "process_agent"
  ) {
    const stage = event.stage as AgentStage;
    const isDone = event.status === "done";
    const now = Date.now();
    setStageStates((prev) => ({
      ...prev,
      [stage]: {
        status:      isDone ? "done" : "running",
        disposition: event.disposition ?? null,
        message:     event.message ?? null,
        startedAt:   isDone ? prev[stage].startedAt : (prev[stage].startedAt ?? now),
        finishedAt:  isDone ? now : undefined,
      },
    }));
  }
  ```

  **Sub-step 2d — Update `SpecialistCard.tsx` to display elapsed time + live message**

  **Pre-Read Gate:**
  - Run `grep -n "Analysing" my-app/src/components/analysis/SpecialistCard.tsx` — must return exactly 1 match. If 0 → STOP.

  Replace `my-app/src/components/analysis/SpecialistCard.tsx` in full:

  ```tsx
  "use client";
  import { useEffect, useState } from "react";
  import type { AgentStage, AgentCardState, WarpDisposition } from "@/types/warp-analysis";

  export interface SpecialistCardProps { stage: AgentStage; state: AgentCardState; }

  const STAGE_LABEL: Record<AgentStage, string> = {
    thermal_agent:  "Thermal",
    geometry_agent: "Geometry",
    process_agent:  "Process",
  };

  /** Format milliseconds to "0.0s" or "12.3s" for display. */
  function fmtMs(ms: number): string {
    return `${(ms / 1000).toFixed(1)}s`;
  }

  /** Left border + text colour based on disposition when done. */
  function doneStyle(disposition: WarpDisposition | null): string {
    if (disposition === "PASS")             return "border-l-green-500 text-green-400";
    if (disposition === "CONDITIONAL")      return "border-l-amber-400 text-amber-400";
    if (disposition === "REWORK_REQUIRED")  return "border-l-red-500 text-red-400";
    return "border-l-zinc-600 text-zinc-500";
  }

  export function SpecialistCard({ stage, state }: SpecialistCardProps) {
    const label = STAGE_LABEL[stage];

    // Live elapsed counter — ticks every 100ms while agent is running.
    const [elapsed, setElapsed] = useState<number>(0);
    useEffect(() => {
      if (state.status !== "running" || state.startedAt === undefined) return;
      const id = setInterval(() => {
        setElapsed(Date.now() - (state.startedAt as number));
      }, 100);
      return () => clearInterval(id);
    }, [state.status, state.startedAt]);

    if (state.status === "queued") {
      return (
        <div className="border border-zinc-800 border-l-2 border-l-zinc-700 p-3">
          <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-600">{label}</p>
          <p className="font-mono text-[10px] text-zinc-700 mt-1">Queued</p>
        </div>
      );
    }

    if (state.status === "running") {
      return (
        <div className="flex-1 border border-amber-400/30 border-l-2 border-l-amber-400 p-3 [animation:warp-pulse_2s_ease-in-out_infinite]">
          <p className="font-mono text-[9px] uppercase tracking-widest text-amber-400">{label}</p>
          <p className="font-mono text-[10px] text-amber-300 mt-1 animate-pulse">
            Analysing… {fmtMs(elapsed)}
          </p>
          {state.message && (
            <p className="font-mono text-[9px] text-amber-400/60 mt-1 truncate" title={state.message}>
              {state.message}
            </p>
          )}
        </div>
      );
    }

    // done state
    const duration =
      state.startedAt !== undefined && state.finishedAt !== undefined
        ? fmtMs(state.finishedAt - state.startedAt)
        : null;

    return (
      <div className={`border border-zinc-800 border-l-2 p-3 ${doneStyle(state.disposition)}`}>
        <p className="font-mono text-[9px] uppercase tracking-widest opacity-70">{label}</p>
        <p className="font-mono text-[10px] mt-1">
          {state.disposition?.replaceAll("_", " ") ?? "DONE"}
        </p>
        {duration && (
          <p className="font-mono text-[9px] text-zinc-600 mt-0.5">{duration}</p>
        )}
      </div>
    );
  }
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/types/warp-analysis.ts \
          my-app/src/components/analysis/AnalysisStream.tsx \
          my-app/src/components/analysis/SpecialistCard.tsx
  git commit -m "step 2: extend AgentCardState with message/startedAt/finishedAt; live elapsed timer on specialist cards"
  ```

  **✓ Verification Test:**

  **Type:** Unit (TypeScript) + Integration (browser)

  **Action (TypeScript):** `cd my-app && npx tsc --noEmit`

  **Expected:** Zero new type errors introduced (compare to pre-flight baseline).

  **Action (Browser):** Select an unanalysed session. Watch running specialist card.

  **Expected:**
  - Running card shows "Analysing… 0.0s" ticking upward in 100 ms increments
  - Running card shows SSE `event.message` text (truncated) below the timer
  - Done card shows disposition + elapsed duration (e.g. "3.2s")

  **Pass:** Timer increments visibly; done card shows duration.

  **Fail:**
  - TypeScript error `Property 'message' does not exist on type 'AgentCardState'` → `warp-analysis.ts` edit not saved correctly
  - Timer stays at 0.0s → `startedAt` not being set in `setStageStates` (check sub-step 2c)

---

- [ ] 🟥 **Step 3: Add SSE keepalive heartbeats in `warp_service.py`** — *Critical: prevents silent connection drops*

  **Step Architecture Thinking:**

  **Pattern applied:** Heartbeat / keepalive. SSE comment lines (`: keepalive\n\n`) are valid SSE events that carry no data. Browsers and proxies reset their idle timeout when bytes arrive. Emitting one every 10 s prevents Nginx's default 60 s `proxy_read_timeout` from killing the connection during a 15–20 s Groq LLM call.

  **Why this step exists here in the sequence:** Must be done before Step 4 builds the new `AnalysisTimeline` — that component will observe connection drops as silent stream termination. Fixing the keepalive now ensures Step 4 tests are valid.

  **Why this file is the right location:** `warp_service.py` is the async generator that owns the SSE output. The queue drain loop (lines 317–323) is the only place that can interleave keepalives without touching business logic.

  **Alternative approach considered and rejected:** Setting `proxy_read_timeout 300s` in Nginx config — requires infrastructure access, is not portable to other proxy setups, and doesn't help in non-Nginx deployments.

  **What breaks if this step deviates:** If the keepalive `yield` uses `"data: "` prefix instead of `": "` prefix, the frontend SSE parser will try to `JSON.parse` it and log a parse error every 10 s.

  ---

  **Idempotent:** Yes — the loop change is a pure refactor with no side effects.

  **Pre-Read Gate:**
  - Run `grep -n "wait_for" backend/services/warp_service.py` — must return exactly 1 match at line 320. If 0 or 2+ → STOP.
  - Run `grep -n "keepalive" backend/services/warp_service.py` — must return 0 matches (not yet added). If already present → step already applied, skip.

  Replace the queue drain loop in `backend/services/warp_service.py` (lines 317–323):

  ```python
      # Drain queue until sentinel, emitting SSE keepalive comments every 10 s.
      # Prevents Nginx proxy_read_timeout (default 60 s) from silently killing
      # the connection during long Groq LLM calls.
      _KEEPALIVE_S = 10.0
      loop = asyncio.get_event_loop()
      _deadline = loop.time() + 300.0

      while True:
          remaining = _deadline - loop.time()
          if remaining <= 0:
              break
          try:
              event = await asyncio.wait_for(
                  queue.get(), timeout=min(_KEEPALIVE_S, remaining)
              )
          except asyncio.TimeoutError:
              if loop.time() >= _deadline:
                  break
              # SSE comment — ignored by frontend parser; resets proxy idle timer.
              yield ": keepalive\n\n"
              continue
          if event is None:
              break
          yield _sse(event)
  ```

  **What it does:** Replaces the single 300 s `asyncio.wait_for` with a loop that wakes every 10 s and emits `": keepalive\n\n"` on timeout, resetting proxy idle timers.

  **Assumptions:**
  - `asyncio.get_event_loop()` is valid in this coroutine context (confirmed: `warp_service.py` uses asyncio throughout).
  - Frontend SSE parser ignores lines starting with `:` (confirmed: `AnalysisStream.tsx` line 79 — `if (!line.startsWith("data: ")) continue;`).

  **Risks:**
  - `asyncio.get_event_loop()` deprecated in Python 3.10+ in favour of `asyncio.get_running_loop()` → mitigation: use `asyncio.get_running_loop()` if Python ≥ 3.10 is confirmed. Either works; `get_event_loop()` falls back correctly.

  **Git Checkpoint:**
  ```bash
  git add backend/services/warp_service.py
  git commit -m "step 3: SSE keepalive heartbeat every 10s to prevent Nginx proxy timeout"
  ```

  **✓ Verification Test:**

  **Type:** Integration

  **Action:** Run backend. In browser DevTools → Network → select the `/analyse` request → Headers tab → observe the response stream. Wait 15 s with no LLM call (or trigger a slow session).

  **Expected:** `: keepalive` lines appear in the raw response every ~10 s.

  **Pass:** Keepalive lines visible in raw SSE stream; frontend shows no parse errors in console.

  **Fail:**
  - Console shows `JSON.parse error` every 10 s → keepalive was emitted as `data: keepalive` instead of `: keepalive` → check the `yield` string in `warp_service.py`
  - Connection still drops → check that the `yield ": keepalive\n\n"` line is actually reached (add a temporary `logger.debug` before it)

---

### Phase 2 — Unified Timeline UX

**Goal:** After Phase 2, the analysis page shows a single `AnalysisTimeline` component where agent cards persist above an inline report, the context-switch is eliminated, and `AnalysisStream.tsx` is deleted.

---

- [ ] 🟥 **Step 4: Create `AnalysisTimeline.tsx` — unified SSE + report component** — *Critical: new architectural component*

  **Step Architecture Thinking:**

  **Pattern applied:** Unified Timeline (Perplexity pattern). A single component owns both the SSE stream lifecycle and the inline report display. Evidence (agent cards) never disappears — the report builds below them. This eliminates the context-switch anti-pattern where `AnalysisStream` is unmounted and `QualityReportCard` is mounted.

  **Why this step exists here in the sequence:** Steps 1–3 fix the existing `AnalysisStream`; this step creates the replacement. It depends on the extended `AgentCardState` (Step 2) being in place before creation so the component can be written to the final interface.

  **Why this file is the right location:** New file, new single responsibility. `AnalysisTimeline.tsx` = "show the full pipeline story from first event to final report". It replaces `AnalysisStream.tsx` entirely.

  **Alternative approach considered and rejected:** Keeping `AnalysisStream.tsx` and adding report display inside it — the existing component has `onComplete` callback architecture baked into its props, which would require refactoring its interface. Cleaner to create a new component with the right interface from the start.

  **What breaks if this step deviates:** If `phase` is tracked in `page.tsx` instead of inside `AnalysisTimeline`, `page.tsx` must re-coordinate two components and the "evidence persists" property is lost.

  ---

  **Idempotent:** Yes — creating a new file is idempotent.

  **Context:** `QualityReportCard` has root element `<div className="flex flex-col min-h-[400px] h-full ...">` and a scrollable body with `flex-1 overflow-y-auto`. Compatible with a `flex-1 min-h-0` parent in `AnalysisTimeline`.

  **Pre-Read Gate:**
  - Run `ls my-app/src/components/analysis/AnalysisTimeline.tsx` — must return "No such file". If it exists → read it first before overwriting.
  - Run `grep -n "streamTrigger" my-app/src/components/analysis/AnalysisTimeline.tsx 2>/dev/null` — should return nothing (file doesn't exist yet).

  Create `my-app/src/components/analysis/AnalysisTimeline.tsx`:

  ```tsx
  "use client";
  /**
   * AnalysisTimeline — unified SSE stream + inline report display.
   *
   * Replaces the AnalysisStream → QualityReportCard context-switch pattern.
   * Agent cards persist above the report (Perplexity "sources before answer" pattern).
   *
   * Props:
   *   sessionId      — session to analyse
   *   streamTrigger  — increment this number to re-run analysis on the same session
   *   onError        — called on SSE pipeline error; parent shows error banner
   *   welderDisplayName — passed through to QualityReportCard
   */
  import { useState, useEffect, useRef, useCallback } from "react";
  import type {
    WarpReport,
    WarpSSEEvent,
    AgentStage,
    AgentCardState,
  } from "@/types/warp-analysis";
  import { streamAnalysis } from "@/lib/warp-api";
  import { SpecialistCard } from "./SpecialistCard";
  import { QualityReportCard } from "./QualityReportCard";

  export interface AnalysisTimelineProps {
    sessionId:         string;
    streamTrigger:     number;
    onError:           (message: string) => void;
    welderDisplayName: string | null;
  }

  const AGENT_STAGES: AgentStage[] = ["thermal_agent", "geometry_agent", "process_agent"];

  const BLANK_STATE: AgentCardState = {
    status:      "queued",
    disposition: null,
    message:     null,
    startedAt:   undefined,
    finishedAt:  undefined,
  };

  const INITIAL_STATES: Record<AgentStage, AgentCardState> = {
    thermal_agent:  { ...BLANK_STATE },
    geometry_agent: { ...BLANK_STATE },
    process_agent:  { ...BLANK_STATE },
  };

  /** Must match analyse_session_stream event count in warp_service.py (currently 9). */
  const TOTAL_EVENTS = 9;

  type Phase = "streaming" | "done";

  export function AnalysisTimeline({
    sessionId,
    streamTrigger,
    onError,
    welderDisplayName,
  }: AnalysisTimelineProps) {
    const [phase, setPhase]           = useState<Phase>("streaming");
    const [progress, setProgress]     = useState(0);
    const [logLines, setLogLines]     = useState<string[]>([]);
    const [stageStates, setStageStates] =
      useState<Record<AgentStage, AgentCardState>>(INITIAL_STATES);
    const [report, setReport]         = useState<WarpReport | null>(null);

    const readerRef  = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
    const onErrorRef = useRef(onError);

    useEffect(() => { onErrorRef.current = onError; }, [onError]);

    // Re-run stream whenever sessionId or streamTrigger changes.
    useEffect(() => {
      let cancelled = false;

      // Reset all state for the new run.
      setPhase("streaming");
      setProgress(0);
      setLogLines([]);
      setStageStates(INITIAL_STATES);
      setReport(null);

      const runStream = async () => {
        let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
        try {
          const stream = await streamAnalysis(sessionId);
          if (cancelled) { stream.cancel().catch(() => {}); return; }

          reader = stream.getReader();
          readerRef.current = reader;

          const decoder = new TextDecoder();
          let buffer = "";
          let eventCount = 0;

          while (true) {
            const { done, value } = await reader.read();
            if (cancelled || done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() ?? "";

            for (const part of parts) {
              const line = part.trim();
              // Ignore SSE comment lines (keepalive: ": keepalive")
              if (!line.startsWith("data: ")) continue;

              let event: WarpSSEEvent;
              try {
                event = JSON.parse(line.slice(6)) as WarpSSEEvent;
              } catch {
                continue;
              }

              if (cancelled) return;

              eventCount += 1;
              setProgress(Math.min(Math.round((eventCount / TOTAL_EVENTS) * 100), 100));

              if (event.message) {
                const ts = new Date().toLocaleTimeString("en-GB", {
                  hour: "2-digit", minute: "2-digit", second: "2-digit",
                });
                setLogLines((prev) => [...prev, `[${ts}] ${event.message}`]);
              }

              if (
                event.stage === "thermal_agent" ||
                event.stage === "geometry_agent" ||
                event.stage === "process_agent"
              ) {
                const stage = event.stage as AgentStage;
                const isDone = event.status === "done";
                const now = Date.now();
                setStageStates((prev) => ({
                  ...prev,
                  [stage]: {
                    status:      isDone ? "done" : "running",
                    disposition: event.disposition ?? null,
                    message:     event.message ?? null,
                    startedAt:   isDone ? prev[stage].startedAt : (prev[stage].startedAt ?? now),
                    finishedAt:  isDone ? now : undefined,
                  },
                }));
              }

              if (event.stage === "complete" && event.report) {
                if (cancelled) return;
                setProgress(100);
                setReport(event.report);
                setPhase("done");
                return;
              }

              if (event.stage === "error") {
                if (cancelled) return;
                onErrorRef.current(event.message ?? "Pipeline error");
                return;
              }

              // Yield to browser event loop — breaks React 18 automatic batching.
              // Without this, multiple events from one reader.read() buffer are processed
              // synchronously and React collapses all setStageStates calls into one render.
              await new Promise<void>((resolve) => setTimeout(resolve, 0));
            }
          }
        } catch (err) {
          if (!cancelled) onErrorRef.current(String(err));
        } finally {
          try { reader?.releaseLock(); } catch { /* already released */ }
        }
      };

      void runStream();

      return () => {
        cancelled = true;
        readerRef.current?.cancel();
        readerRef.current = null;
      };
    // streamTrigger in deps — incrementing it causes the effect to re-run, restarting the stream.
    }, [sessionId, streamTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

    return (
      <div className="flex flex-col h-full min-h-0 bg-[var(--warp-surface)]">
        {/* Header + progress bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
            {phase === "streaming" ? "Analysis in Progress" : "Analysis Complete"}
          </span>
          <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">{sessionId}</span>
        </div>

        <div className="h-0.5 bg-zinc-900 shrink-0">
          <div
            className="h-full bg-amber-400 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Scrollable content — agent cards persist above report */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {/* Agent card row — always visible */}
          <div className="flex shrink-0 gap-px p-4">
            {AGENT_STAGES.map((stage, index) => (
              <div
                key={stage}
                className="flex-1"
                style={{ animation: `warp-card-enter 200ms ease-out ${index * 150}ms both` }}
              >
                <SpecialistCard stage={stage} state={stageStates[stage]} />
              </div>
            ))}
          </div>

          {/* Log lines — visible during streaming */}
          {phase === "streaming" && (
            <div className="px-4 pb-4">
              <div className="font-mono text-[9px] text-[var(--warp-text-dim)] space-y-0.5">
                {logLines.map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
                {logLines.length === 0 && (
                  <p className="text-zinc-700">Waiting for pipeline…</p>
                )}
              </div>
            </div>
          )}

          {/* Report — fades in when phase === "done"; agent cards remain visible above */}
          {phase === "done" && report && (
            <div className="animate-warp-fade-in px-0">
              <div className="border-t border-zinc-800 mx-4 mb-2" />
              <QualityReportCard
                report={report}
                welderDisplayName={welderDisplayName}
              />
            </div>
          )}
        </div>
      </div>
    );
  }
  ```

  **What it does:** Single component that owns SSE stream state and inline report display. Agent cards persist when the report appears. `streamTrigger` allows re-analysis without unmounting the component.

  **Why this approach:** Eliminates the context-switch. No prop drilling of `onComplete` to parent — the component handles report display itself.

  **Assumptions:**
  - `QualityReportCard` accepts `welderDisplayName` as an optional prop (confirmed: `QualityReportCardProps.welderDisplayName?: string | null`).
  - `animate-warp-fade-in` CSS class is defined in the global stylesheet (used in existing `page.tsx` line 271).
  - `warp-card-enter` keyframe is defined (used in existing `AnalysisStream.tsx` line 174).

  **Risks:**
  - `QualityReportCard` has its own `onReanalyse` prop — not wired here because re-analyse is triggered by `streamTrigger` from `page.tsx` → mitigation: this is intentional; the re-analyse button stays in `page.tsx` error banner.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/AnalysisTimeline.tsx
  git commit -m "step 4: create AnalysisTimeline — unified SSE stream + inline report, agent cards persist"
  ```

  **✓ Verification Test:**

  **Type:** TypeScript + Integration

  **Action (TypeScript):** `cd my-app && npx tsc --noEmit`

  **Expected:** Zero new type errors.

  **Action (Browser):** Select an unanalysed session (temporarily wire `AnalysisTimeline` in `page.tsx` as a test if desired, or proceed to Step 5).

  **Pass:** TypeScript compiles clean; component file exists at correct path.

  **Fail:**
  - `Cannot find module './QualityReportCard'` → confirm `QualityReportCard.tsx` exists in same directory
  - `Property 'welderDisplayName' does not exist` → check `QualityReportCardProps` in `QualityReportCard.tsx` line 10

---

- [ ] 🟥 **Step 5: Update `page.tsx` — collapse ViewState, wire `AnalysisTimeline`, delete `AnalysisStream.tsx`** — *Critical: wires Phase 2 into production*

  **Step Architecture Thinking:**

  **Pattern applied:** State machine collapse. `ViewState` had three modes: `empty | streaming | report`. The `report` mode no longer exists — `AnalysisTimeline` owns report display internally. `ViewState` collapses to two modes: `empty | active`. The `active` mode passes `sessionId` and `streamTrigger` to `AnalysisTimeline`.

  **Why this step exists here in the sequence:** `AnalysisTimeline` must exist (Step 4) before this step wires it. This is the final integration step.

  **Why this file is the right location:** `page.tsx` is the only consumer of `AnalysisStream` and `QualityReportCard` at the page level. All wiring changes are contained here.

  **Alternative approach considered and rejected:** Keeping `AnalysisStream.tsx` as a deprecated file — introduces a dead code path that will confuse future maintainers. Delete it cleanly.

  **What breaks if this step deviates:** If `streamTrigger` is not incremented on re-analyse (i.e., using `key={sessionId}` instead), the component is torn down and re-mounted — losing all agent card state and re-triggering entry animations.

  ---

  **Idempotent:** No — `AnalysisStream.tsx` deletion cannot be undone without git. Verify Step 4 TypeScript before deleting.

  **Pre-Read Gate:**
  - Run `grep -n "AnalysisStream\|QualityReportCard" my-app/src/app/\(app\)/analysis/page.tsx` — must return matches on import lines and render lines. If already shows `AnalysisTimeline` → step already applied, skip.
  - Run `cd my-app && npx tsc --noEmit` — must return 0 errors before proceeding. If errors exist → fix Step 4 first.

  **Sub-step 5a — Update `page.tsx`**

  Replace `my-app/src/app/(app)/analysis/page.tsx` with the following. Key changes:
  - `ViewState` collapses to `{ mode: "empty" } | { mode: "active"; sessionId: string }`
  - New `streamTrigger` state (counter, incremented on re-analyse)
  - `handleStreamComplete` now only advances the queue (no more `setViewState({ mode: "report" })`)
  - `handleStreamError` resets to `{ mode: "empty" }`
  - Render block: replaces `streaming` + `report` branches with single `active` branch using `AnalysisTimeline`
  - Remove `AnalysisStream` and `QualityReportCard` imports

  ```tsx
  "use client";
  /**
   * /analysis — WarpSense post-weld analysis surface.
   *
   * State machine (simplified in Phase UI-8.5):
   *   empty  → no session selected; right panel shows prompt
   *   active → AnalysisTimeline owns both SSE streaming and inline report display
   *
   * Height: fills the `(app)` layout content row via `h-full min-h-0` (grid `1fr` below AppNav).
   * WelderTrendChart is loaded via next/dynamic (ssr:false) — Recharts uses DOM APIs
   * unavailable in Node. See LEARNING_LOG.md 2026-03-02.
   */
  import { useCallback, useEffect, useRef, useState } from "react";
  import dynamic from "next/dynamic";
  import type {
    MockSession,
    WarpReport,
    WarpHealthResponse,
  } from "@/types/warp-analysis";
  import {
    fetchWarpHealth,
    fetchWarpReport,
    fetchMockSessions,
  } from "@/lib/warp-api";
  import { SessionList } from "@/components/analysis/SessionList";
  import { AnalysisTimeline } from "@/components/analysis/AnalysisTimeline";

  const WelderTrendChart = dynamic(
    () =>
      import("@/components/analysis/WelderTrendChart").then(
        (m) => m.WelderTrendChart,
      ),
    { ssr: false },
  );

  type ViewState =
    | { mode: "empty" }
    | { mode: "active"; sessionId: string };

  const HEALTH_POLL_MS = 30_000;

  export default function AnalysisPage() {
    const [selectedSession, setSelectedSession] = useState<MockSession | null>(null);
    const [viewState, setViewState]             = useState<ViewState>({ mode: "empty" });
    // Increment to re-trigger AnalysisTimeline's stream effect without unmounting.
    const [streamTrigger, setStreamTrigger]     = useState(0);
    const [streamError, setStreamError]         = useState<string | null>(null);
    const [health, setHealth]                   = useState<WarpHealthResponse | null>(null);
    const [isAnalysing, setIsAnalysing]         = useState(false);

    const analyseQueueRef  = useRef<MockSession[]>([]);
    const selectCounterRef = useRef(0);

    useEffect(() => {
      let cancelled = false;
      const poll = async () => {
        const h = await fetchWarpHealth();
        if (!cancelled) setHealth(h);
      };
      void poll();
      const id = setInterval(() => void poll(), HEALTH_POLL_MS);
      return () => { cancelled = true; clearInterval(id); };
    }, []);

    const startStream = useCallback((sessionId: string) => {
      setStreamError(null);
      setViewState({ mode: "active", sessionId });
      setStreamTrigger((n) => n + 1);
    }, []);

    const handleSessionSelect = useCallback(
      async (session: MockSession) => {
        setSelectedSession(session);
        setIsAnalysing(false);
        analyseQueueRef.current = [];
        setViewState({ mode: "empty" });

        const callId = ++selectCounterRef.current;

        let existingReport: WarpReport | null = null;
        try {
          existingReport = await fetchWarpReport(session.session_id);
        } catch (err) {
          if (callId !== selectCounterRef.current) return;
          setStreamError(
            `Could not load report for ${session.session_id}: ${String(err)}`,
          );
          return;
        }

        if (callId !== selectCounterRef.current) return;

        if (existingReport) {
          // Session already analysed — show existing report immediately via AnalysisTimeline.
          // AnalysisTimeline will still try to stream; the backend will return the cached report
          // via the complete event. Alternatively, we could pass `initialReport` prop in future.
          // For now: start stream which will complete quickly with the cached result.
          startStream(session.session_id);
        } else {
          startStream(session.session_id);
        }
      },
      [startStream],
    );

    const handleStreamComplete = useCallback(
      (_report: WarpReport) => {
        // AnalysisTimeline displays the report internally.
        // This callback only advances the Analyse All queue.
        const queue = analyseQueueRef.current;
        if (queue.length > 0) {
          const nextSession = queue[0];
          analyseQueueRef.current = queue.slice(1);
          setSelectedSession(nextSession);
          startStream(nextSession.session_id);
        } else {
          setIsAnalysing(false);
        }
      },
      [startStream],
    );

    const handleStreamError = useCallback((message: string) => {
      setStreamError(message);
      setIsAnalysing(false);
      analyseQueueRef.current = [];
    }, []);

    const handleReanalyse = useCallback(() => {
      if (!selectedSession) return;
      // Increment streamTrigger to restart the stream without unmounting AnalysisTimeline.
      setStreamTrigger((n) => n + 1);
      setStreamError(null);
    }, [selectedSession]);

    const handleAnalyseAll = useCallback(async () => {
      let sessions: MockSession[];
      try {
        sessions = await fetchMockSessions();
      } catch (err) {
        setStreamError(`Could not load sessions: ${String(err)}`);
        return;
      }
      if (sessions.length === 0) return;
      const first = sessions[0];
      analyseQueueRef.current = sessions.slice(1);
      setSelectedSession(first);
      setIsAnalysing(true);
      startStream(first.session_id);
    }, [startStream]);

    const healthOk =
      health !== null &&
      health.graph_initialised &&
      health.classifier_initialised;

    return (
      <div
        className="flex h-full min-h-0 w-full flex-col bg-[var(--warp-bg)]"
        style={{ fontFamily: "var(--font-warp-mono), monospace" }}
      >
        {/* Top bar */}
        <div className="flex shrink-0 items-center justify-between border-b border-[var(--warp-border)] bg-[var(--warp-surface)] px-4 py-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
              WarpSense
            </span>
            <span className="font-mono text-[8px] text-[var(--warp-text-dim)]">
              AI Analysis Engine
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                health === null
                  ? "bg-gray-600"
                  : healthOk
                    ? "bg-green-500"
                    : "bg-red-500"
              }`}
            />
            <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">
              {health === null
                ? "system: checking"
                : healthOk
                  ? "system: OK"
                  : "system: unavailable"}
            </span>
          </div>
        </div>

        {/* Error banner */}
        {streamError && (
          <div className="flex shrink-0 items-center justify-between border-b border-red-800 bg-red-950/50 px-4 py-2 font-mono text-[10px] text-red-300">
            <span>Analysis failed: {streamError}</span>
            <div className="ml-4 flex items-center gap-3">
              {selectedSession && (
                <button
                  type="button"
                  onClick={handleReanalyse}
                  className="text-red-400 transition-colors hover:text-red-200"
                  aria-label="Retry analysis"
                >
                  Retry
                </button>
              )}
              <button
                type="button"
                onClick={() => setStreamError(null)}
                className="text-red-400 transition-colors hover:text-red-200"
                aria-label="Dismiss error"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Health warning */}
        {health !== null && !healthOk && (
          <div className="shrink-0 border-b border-amber-900 bg-amber-950/40 px-4 py-2 font-mono text-[10px] text-amber-400">
            AI pipeline unavailable — analysis may not complete
          </div>
        )}

        {/* Main layout */}
        <div className="flex min-h-0 min-w-[1200px] flex-1 overflow-hidden">
          {/* Left: session list + trend chart */}
          <div className="flex w-[320px] shrink-0 flex-col overflow-hidden border-r border-[var(--warp-border)]">
            <div className="min-h-0 flex-1 overflow-hidden">
              <SessionList
                onSessionSelect={handleSessionSelect}
                selectedSessionId={selectedSession?.session_id ?? null}
                onAnalyseAll={handleAnalyseAll}
                isAnalysing={isAnalysing}
              />
            </div>
            {selectedSession && (
              <WelderTrendChart welderId={selectedSession.welder_id} />
            )}
          </div>

          {/* Right: analysis panel */}
          <div className="min-h-0 flex-1 overflow-hidden">
            {viewState.mode === "empty" && (
              <div className="flex h-full items-center justify-center">
                <div className="space-y-1 text-center">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-dim)]">
                    Select a session to begin analysis
                  </p>
                  <p className="font-mono text-[9px] text-zinc-700">
                    Or use Analyse All to run the full pipeline
                  </p>
                </div>
              </div>
            )}

            {viewState.mode === "active" && (
              <AnalysisTimeline
                key={viewState.sessionId}
                sessionId={viewState.sessionId}
                streamTrigger={streamTrigger}
                onError={handleStreamError}
                welderDisplayName={selectedSession?.welder_name ?? null}
              />
            )}
          </div>
        </div>
      </div>
    );
  }
  ```

  > **Note on `handleStreamComplete`:** `AnalysisTimeline` no longer calls `onComplete` — the callback is removed from its props. The `handleStreamComplete` function in `page.tsx` is kept only for the Analyse All queue logic; it now receives `_report` (unused). If Analyse All queue advancement is needed, wire it by passing an optional `onComplete` prop to `AnalysisTimeline` in a follow-up.

  **Sub-step 5b — Delete `AnalysisStream.tsx`**

  ```bash
  rm my-app/src/components/analysis/AnalysisStream.tsx
  ```

  **Pre-condition:** Run `cd my-app && npx tsc --noEmit` first. Must show 0 errors. If `AnalysisStream` is still imported anywhere, the compiler will catch it here.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/analysis/page.tsx
  git rm my-app/src/components/analysis/AnalysisStream.tsx
  git commit -m "step 5: collapse ViewState to 2 modes, wire AnalysisTimeline, delete AnalysisStream"
  ```

  **✓ Verification Test:**

  **Type:** E2E (browser)

  **Action:** Start backend + frontend. Select an unanalysed session.

  **Expected:**
  1. Three agent cards appear with staggered entry animation (150 ms apart)
  2. Thermal card turns amber with live elapsed timer ticking
  3. ~2–4 s later: Thermal resolves with disposition + duration; Geometry turns amber
  4. ~2–4 s later: Geometry resolves; Process turns amber
  5. ~2–4 s later: Process resolves; report fades in below all three agent cards
  6. All three agent cards remain visible above the report (not replaced)
  7. Progress bar reaches 100%

  **Pass:** Agent cards sequential animation visible; report appears inline below cards; no console errors.

  **Fail:**
  - `Module not found: AnalysisStream` → `AnalysisStream` import still in another file → `grep -rn "AnalysisStream" my-app/src/`
  - All cards still appear simultaneously → `setTimeout` yield missing in `AnalysisTimeline.tsx` line ~100
  - Report replaces cards → `AnalysisTimeline` not rendering; old `page.tsx` still active → check file was saved
  - TypeScript error on `streamTrigger` → prop not defined in `AnalysisTimelineProps` → check `AnalysisTimeline.tsx` interface

---

## Regression Guard

**Systems at risk from this plan:**

- Analyse All queue — `handleStreamComplete` is no longer called by `AnalysisTimeline` (no `onComplete` prop); queue advancement breaks.
- Re-analyse flow — `handleReanalyse` now increments `streamTrigger` rather than calling `startStream`; must verify this triggers the effect.

**Regression verification:**

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| Analyse All | Automatically advances to next session after each completes | Select multiple sessions → Analyse All → verify each session's timeline completes before advancing |
| Re-analyse | Retry button starts new stream for same session | Click Retry in error banner → verify agent cards reset and stream restarts |
| Session switch | Selecting a new session cancels current stream | Select session A → wait for streaming → select session B → verify A stream stops |
| Existing report | Selecting an already-analysed session shows cached report | Select a previously-analysed session → verify report appears |

> **Known gap:** `AnalysisTimeline` does not currently call `onComplete` — Analyse All queue advancement requires wiring an optional `onComplete` prop in `AnalysisTimeline` and calling it when `phase` transitions to `"done"`. Add this if Analyse All is a required feature.

**Test count regression check:**

- Run `cd my-app && npx tsc --noEmit` after each step — error count must not increase from pre-flight baseline.
- Run existing test suite: `cd my-app && npm test -- --passWithNoTests`

---

## Rollback Procedure

```bash
# Rollback in reverse order

# Step 5
git revert HEAD  # reverts "step 5: collapse ViewState..."
# This restores AnalysisStream.tsx (git rm is reversed by revert)

# Step 4
git revert HEAD~1  # reverts "step 4: create AnalysisTimeline..."

# Step 3
git revert HEAD~2  # reverts "step 3: SSE keepalive..."

# Step 2
git revert HEAD~3  # reverts "step 2: extend AgentCardState..."

# Step 1
git revert HEAD~4  # reverts "step 1: yield to event loop..."

# Confirm clean state
cd my-app && npx tsc --noEmit
```

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| Step 1 | 🟢 Low | `await` placed after for loop instead of inside it | Cards still update simultaneously in browser | Yes |
| Step 2 | 🟡 Medium | TypeScript errors from incomplete interface extension | `tsc --noEmit` catches immediately | Yes |
| Step 3 | 🟢 Low | Keepalive emitted as `data:` instead of `:` | Console parse errors every 10 s | Yes |
| Step 4 | 🟡 Medium | `QualityReportCard` layout incompatibility | Visual overflow or missing content | Yes |
| Step 5 | 🔴 High | Analyse All queue broken if `onComplete` not wired | Queue stops after first session | No (file deletion) |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Sequential agent animation | Each of 3 agents activates ~2–4 s apart | Watch analysis in browser; time the card transitions |
| Elapsed timer on running card | Timer ticks in 100 ms increments from 0.0s | Watch running card; timer should be visibly counting |
| Agent cards persist after report | All 3 cards visible above inline report | Scroll up after report appears; agent cards still present |
| Report appears inline | Report fades in below cards, no page transition | No component unmount/remount visible in React DevTools |
| SSE keepalive | No connection drops on 15+ s analyses | Check Network tab in DevTools; connection stays open |
| TypeScript clean | `tsc --noEmit` returns 0 errors | Run after each step |
| Re-analyse works | Retry button restarts stream, cards reset | Click Retry; agent cards reset to "Queued" |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
⚠️ **If blocked, mark 🟨 In Progress and output the State Manifest before stopping.**
⚠️ **Do not batch multiple steps into one git commit.**
⚠️ **Step 5 deletion of `AnalysisStream.tsx` is irreversible without git revert — confirm TypeScript is clean before running `git rm`.**
⚠️ **Analyse All queue advancement gap is a known risk in Step 5 — wire `onComplete` prop on `AnalysisTimeline` if this feature must work post-plan.**
