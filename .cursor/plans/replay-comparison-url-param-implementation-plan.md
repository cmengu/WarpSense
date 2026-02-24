# Replay Comparison URL Param — Implementation Plan

**Overall Progress:** `100%`

## TLDR

Add `?compare=sess_id` URL param to the replay page so comparison session can be chosen via shareable link. When present, URL overrides env. Also pre-fill both A and B on the compare page link when a comparison is active, and show a same-session warning (warn, don't block). Option C (dropdown) can be layered later via `router.replace(?compare=…)` — document for future implementers.

---

## Critical Decisions

- **effectiveComparisonId logic:** `compareParam?.trim() || COMPARISON_SESSION_ID || undefined` — avoids confusing `??`/`||` mix. URL param wins when non-empty; else env; else undefined (no fetch).
- **Compare page link:** Pre-fill both sessionA and sessionB when `effectiveComparisonId` is set. One-link jump from replay to compare page with both sessions.
- **Same-session guard:** Warn only — console warning + visual "Comparing with itself" indicator. No blocking.
- **Option C (dropdown) future path:** Document that a dropdown need only call `router.replace(?compare=<id>)`; all other logic is already wired.

---

## Tasks

### Phase 1 — Replay Page URL Param & Compare Link

**Goal:** User can share `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001` and get side-by-side comparison. "Compare with another session" link pre-fills both A and B when comparison is active.

---

- [x] 🟩 **Step 1: Derive effectiveComparisonId from URL and update comparison fetch** — *Critical: state management, API integration*

  **Context:** The comparison session fetch currently uses only `COMPARISON_SESSION_ID` from env. We add URL param `?compare=` that overrides env when present. This drives shareable links.

  **Code:**
  ```ts
  // After tParam / initialTimestampMs (around line 200), add:
  const compareParam = searchParams.get('compare');
  const effectiveComparisonId =
    compareParam?.trim() || COMPARISON_SESSION_ID || undefined;

  // Replace existing comparison fetch useEffect (lines 365–401):
  useEffect(() => {
    if (!showComparison || !effectiveComparisonId) {
      setComparisonSession(null);
      return;
    }

    let cancelled = false;
    const loadComparison = async () => {
      try {
        const data = await fetchSession(effectiveComparisonId, {
          limit: 2000,
          include_thermal: true,
        });
        if (!cancelled) setComparisonSession(data);
      } catch (err) {
        if (!cancelled) {
          logWarn(
            "ReplayPage",
            `Comparison session ${effectiveComparisonId} not found or failed to load`,
            { error: err instanceof Error ? err.message : String(err) }
          );
          setComparisonSession(null);
        }
      }
    };

    loadComparison();
    return () => {
      cancelled = true;
    };
  }, [showComparison, effectiveComparisonId]);
  ```

  **What it does:** Reads `compare` from URL; `effectiveComparisonId` is URL param (trimmed) or env fallback. Fetch uses that ID. Deps ensure refetch when URL or env changes.

  **Why this approach:** `compareParam?.trim() || COMPARISON_SESSION_ID || undefined` cleanly orders: non-empty URL → env → none. Avoids `??`/`||` confusion.

  **Assumptions:**
  - `searchParams.get('compare')` returns string or null.
  - COMPARISON_SESSION_ID is `string | undefined` from getComparisonSessionId().

  **Risks:**
  - Stale closure if deps wrong → verify `effectiveComparisonId` in deps.
  - Race on fast URL changes → cancellation in cleanup mitigates.

  **Subtasks:**
  - [ ] 🟥 Add `compareParam` and `effectiveComparisonId` derivation.
  - [ ] 🟥 Replace comparison fetch useEffect to use `effectiveComparisonId` and update deps.

  **✓ Verification Test:**

  **Pre-flight (run first — confirms DB ready; avoids debugging frontend when data is stale):**
  ```bash
  curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001 | python3 -c "
  import sys, json
  d = json.load(sys.stdin)
  assert len(d.get('frames', [])) == 1500, 'FAIL: expert aluminium not seeded correctly'
  "
  curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001 | python3 -c "
  import sys, json
  d = json.load(sys.stdin)
  assert len(d.get('frames', [])) == 1500, 'FAIL: novice aluminium not seeded correctly'
  "
  echo "OK — both sessions ready for comparison test"
  ```
  If either assertion fails, run `cd backend && python -m scripts.seed_demo_data --force`, then re-run.

  **Action:**
  - Start dev server
  - Navigate to `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001`

  **Expected Result:**
  - Left panel: Current Session (sess_expert_aluminium_001_001)
  - Right panel: Comparison (sess_novice_aluminium_001_001) with 3D heatmap and score
  - No console errors

  **How to Observe:**
  - **Visual:** Both 3D panels render; right panel label shows sess_novice_aluminium_001_001
  - **Console:** No fetch/404 errors for comparison session

  **Pass Criteria:**
  - Pre-flight curl assertions pass
  - Both panels show thermal 3D visualization
  - Right label shows comparison session ID from URL

  **Common Failures & Fixes:**
  - **If pre-flight fails:** DB stale — run `python -m scripts.seed_demo_data --force`
  - **If right panel shows "Comparison session not available":** Check backend has sess_novice_aluminium_001_001; rerun pre-flight
  - **If right panel shows env session instead of URL:** Verify `effectiveComparisonId` uses `compareParam` first; check searchParams.get('compare')

---

- [x] 🟩 **Step 2: Update score fetch and 3D label to use effectiveComparisonId**

  **Context:** Score fetch and TorchWithHeatmap3D label currently use COMPARISON_SESSION_ID. They must use effectiveComparisonId so scores and label match the actually loaded comparison session.

  **Code:**
  ```ts
  // In score fetch useEffect (lines 428–434), replace:
  if (
    showComparison &&
    effectiveComparisonId &&
    comparisonSession
  ) {
    fetchScore(effectiveComparisonId)
      // ... rest unchanged, and fix log message to use effectiveComparisonId
  }

  // In TorchWithHeatmap3D label (line 807), replace:
  label={`Comparison (${effectiveComparisonId ?? 'unknown'})`}
  ```

  **What it does:** Score fetch and label use the same ID as the comparison fetch.

  **Assumptions:** effectiveComparisonId is in scope where score useEffect runs (must be defined earlier in component).

  **Subtasks:**
  - [ ] 🟥 Update score fetch condition and fetchScore argument to use effectiveComparisonId
  - [ ] 🟥 Update TorchWithHeatmap3D label prop

  **✓ Verification Test:**

  **Action:** Load `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001`

  **Expected Result:** Right panel shows "Comparison (sess_novice_aluminium_001_001)" and that session's score.

  **Pass Criteria:** Label and score match URL param session.

---

- [x] 🟩 **Step 3: Pre-fill Compare page link with sessionB when effectiveComparisonId is set**

  **Context:** "Compare with another session" link currently only passes sessionA. When a comparison is active, adding sessionB makes the compare page useful from replay with one click.

  **Code:**
  ```ts
  // Replace Link href (line 579):
  href={`/compare?sessionA=${encodeURIComponent(sessionId)}${
    effectiveComparisonId
      ? `&sessionB=${encodeURIComponent(effectiveComparisonId)}`
      : ''
  }`}
  ```

  **What it does:** When effectiveComparisonId exists, link includes &sessionB=... so compare form has both fields pre-filled.

  **Subtasks:**
  - [ ] 🟥 Update Compare link href

  **✓ Verification Test:**

  **Action:**
  - Load replay with comparison: `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001`
  - Click "Compare with another session"

  **Expected Result:** Compare form shows Session A = sess_expert_aluminium_001_001, Session B = sess_novice_aluminium_001_001; Compare button enabled

  **Pass Criteria:** Both inputs pre-filled; can click Compare and land on compare page.

  **Common Failures & Fixes:**
  - **If Session B empty:** Compare page must read sessionB from searchParams — see Step 6

---

- [x] 🟩 **Step 4: Same-session warning (warn, don't block)**

  **Context:** When ?compare= equals current sessionId, user sees two identical 3D views. Warn instead of blocking.

  **Code:**
  ```ts
  // After effectiveComparisonId, add:
  const isComparingWithSelf =
    effectiveComparisonId != null &&
    effectiveComparisonId === sessionId;

  // Optional: useEffect to log once when isComparingWithSelf
  useEffect(() => {
    if (isComparingWithSelf && typeof console?.warn === 'function') {
      console.warn(
        `ReplayPage: Comparing session with itself (${sessionId}). Consider using a different ?compare= value.`
      );
    }
  }, [isComparingWithSelf, sessionId]);

  // In right panel, when rendering TorchWithHeatmap3D, add above/below a small banner when isComparingWithSelf:
  {isComparingWithSelf && (
    <div className="mb-2 px-3 py-1.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 text-xs">
      Comparing with itself
    </div>
  )}
  ```

  **What it does:** Detects same session; logs console warning; shows amber "Comparing with itself" banner in right column.

  **Subtasks:**
  - [ ] 🟥 Add isComparingWithSelf derived value
  - [ ] 🟥 Add useEffect for console.warn
  - [ ] 🟥 Add visual banner in right panel when isComparingWithSelf

  **✓ Verification Test:**

  **Action:** Load `/replay/sess_expert_aluminium_001_001?compare=sess_expert_aluminium_001_001`

  **Expected Result:** Both panels render; amber "Comparing with itself" banner under right panel; console has warning

  **Pass Criteria:** Banner visible; no blocking; comparison still works.

---

- [x] 🟩 **Step 5: Document Option C future path for dropdown implementers**

  **Context:** A future dropdown (Option C) should not re-architect. It only needs to update the URL.

  **Code:**
  ```ts
  // Add inline comment near effectiveComparisonId (or in exploration doc):
  // Future Option C (dropdown): A selector can call router.replace(`?compare=${selectedId}`)
  // or `router.push` with updated searchParams. effectiveComparisonId will update from
  // searchParams; the existing fetch/label/score logic requires no changes.
  ```

  **Subtasks:**
  - [ ] 🟥 Add comment in replay page near effectiveComparisonId

  **✓ Verification Test:** Comment exists; no logic change.

---

### Phase 2 — Compare Page sessionB Pre-fill

**Goal:** Compare form pre-fills Session B when arriving via `/compare?sessionA=X&sessionB=Y`.

---

- [x] 🟩 **Step 6: Read sessionB from URL and pre-fill Compare form**

  **Context:** Compare page only reads sessionA from searchParams. We add sessionB so replay link with both params works.

  **Code:**
  ```ts
  // In CompareForm (my-app/src/app/compare/page.tsx), replace:
  const sessionAFromQuery = searchParams.get('sessionA') ?? '';
  const sessionBFromQuery = searchParams.get('sessionB') ?? '';
  const [sessionIdA, setSessionIdA] = useState(sessionAFromQuery);
  const [sessionIdB, setSessionIdB] = useState(sessionBFromQuery);
  ```

  **Add this comment directly above the useState lines for sessionIdA/sessionIdB (so future developers see it):**
  ```ts
  // Note: useState initializes from URL on mount only.
  // In-place URL edits (e.g. back/forward navigation) will not sync inputs.
  // Acceptable for MVP; fix by adding useEffect to sync if sessionBFromQuery changes.
  ```

  **What it does:** Both inputs initialize from URL. Navigation from replay with both params pre-fills the form.

  **Subtasks:**
  - [ ] 🟥 Add sessionBFromQuery and pass to useState for sessionIdB
  - [ ] 🟥 Add the useState caveat comment above the state declarations

  **✓ Verification Test:**

  **Action:** Open `/compare?sessionA=sess_expert_aluminium_001_001&sessionB=sess_novice_aluminium_001_001` directly (or via replay link)

  **Expected Result:** Both Session A and Session B inputs show the corresponding IDs; Compare button enabled

  **Pass Criteria:** Form pre-filled; Compare navigates to /compare/A/B correctly; caveat comment present in code

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Backend running | `curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001` returns 200 | ⬜ |
| | Demo data seeded | Run Step 1 pre-flight curl assertions | ⬜ |
| | useSearchParams available | Replay page already uses it for ?t= | ⬜ |
| **Phase 2** | Compare page loads | `/compare` renders form | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟡 **30%** | effectiveComparisonId wrong when compare param empty | Test without ?compare= — should use env; if env unset, no comparison fetch | ⬜ |
| Phase 1 | 🟡 **25%** | Score fetch still uses COMPARISON_SESSION_ID | Right panel shows wrong session's score when using ?compare= | ⬜ |
| Phase 2 | 🟢 **10%** | sessionB not pre-filling | Click from replay with ?compare= — Session B should be filled | ⬜ |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|----------------|---------------------|
| Shareable replay link | `/replay/sess_expert_aluminium_001_001?compare=sess_novice_aluminium_001_001` shows both 3D panels | Load URL → both panels render with correct labels |
| Compare link pre-fill | From replay with comparison, "Compare with another session" opens form with A and B filled | Click link → both inputs populated; Compare works |
| Same-session | `?compare=` same as sessionId shows "Comparing with itself" | Load URL → banner + console warning; no block |
| Env fallback | No ?compare= uses NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID | Remove ?compare= from URL → env session used |

---

## Option C (Dropdown) — Future Implementation Note

When adding a compare session selector dropdown:

1. **Do not** change effectiveComparisonId derivation or fetch logic.
2. **Do** add a `<select>` (or similar) that calls `router.replace(/replay/${sessionId}?compare=${selectedId})` or equivalent.
3. searchParams updates → effectiveComparisonId updates → existing useEffect refetches. No further changes needed.

This is documented in `.cursor/plans/replay-comparison-url-param-exploration.md` and in the inline comment (Step 5).
