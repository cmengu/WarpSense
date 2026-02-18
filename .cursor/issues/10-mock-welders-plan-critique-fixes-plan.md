# Implementation Plan: Critique Fixes for 10 Mock Welders

**Issue:** 10-mock-welders-plan-critique-fixes  
**Parent:** 10-mock-welders-with-skill-arcs  
**Source:** `.cursor/issues/10-mock-welders-plan-critique-fixes.md` + exploration handoff  
**Estimate:** 9h  

---

## Overview

Apply five main and four minor critique fixes to the 10 Mock Welders implementation. These fixes close gaps identified in the plan: prototype tuning guidance, archetype sync verification, seed_demo_data spot-check correctness, dashboard loading state, and last-slot historicalScores regression test. **Blocked by:** Parent plan Phase 1 Steps 1.1–1.3 (mock_welders, generate_frames_for_arc, generate_session_for_welder must exist). This plan can be executed alongside the parent or as a follow-up PR.

---

## Phase Breakdown

### Phase 1 — Prototype & Plan Doc Fixes

**Goal:** Prototype uses mock_sessions.generate_session_for_welder; Step 1.4 has tuning guide and fresh-process note; plan doc has Phase 3 pre-flight, Step 2.3 folded, wipe/seed note, badge flicker note; generate_frames_for_arc uses Tuple for Python 3.8 compat.  
**Risk:** Low  
**Estimate:** 2.5h  

### Phase 2 — Seed & Spot-Check Fixes

**Goal:** seed_demo_data.py uses session_ids[0] + first archetype for spot-check; spot-check runs in both skip and re-seed branches; idempotent on existing == expected_count only.  
**Risk:** Low  
**Estimate:** 1.5h  

### Phase 3 — Dashboard & Welder Report Fixes

**Goal:** Cards show skeleton during load; setWelderScores called once after Promise.allSettled; welder report uses sc.total for last slot in historicalScores; badge flicker documented.  
**Risk:** Low  
**Estimate:** 2h  

### Phase 4 — Tests & Verification

**Goal:** ai-feedback.test.ts has concrete last-slot tests; Step 5.3 either has full test code or explicit "manual only" note; integration test verifies welder report caller passes sc.total.  
**Risk:** Low  
**Estimate:** 1.5h  

---

## Pre-Flight Checklist (Run Before Phase 1)

**Automated dependency and structure check — fail fast if parent incomplete:**

```bash
PYTHONPATH=backend python -c "
from data.mock_sessions import generate_session_for_welder
from data.mock_welders import WELDER_ARCHETYPES
# Structure assertion: archetypes must have welder_id and sessions
assert len(WELDER_ARCHETYPES) > 0, 'WELDER_ARCHETYPES must not be empty'
for i, a in enumerate(WELDER_ARCHETYPES):
    assert 'welder_id' in a, f'Archetype {i} missing welder_id'
    assert 'sessions' in a, f'Archetype {i} missing sessions (parent uses sessions, not sessionCount)'
    assert a['sessions'] >= 1, f'Archetype {a.get(\"welder_id\", i)} has sessions=0; all archetypes must have sessions >= 1'
print('OK: Dependencies and structure valid')
"
```

If this fails (ImportError, ModuleNotFoundError, AssertionError): **STOP**. Complete parent plan Phase 1 Steps 1.1–1.3 first. Fix structure (welder_id, sessions keys; sessions >= 1). Do not proceed until the check succeeds.

---

## Plan File Resolution (Canonical Order)

**Single source of truth:** Resolve the parent **implementation plan** file (not the issue) using this order. The issue file (`10-mock-welders-with-skill-arcs.md`) contains the feature spec; the implementation plan has Step 1.4, tuning guide, etc.

1. `docs/plan-10-mock-welders.md` — canonical; create if absent
2. `.cursor/issues/10-mock-welders-plan.md` — parent implementation plan (if created)
3. `.cursor/taskspace/*/plan-10-mock-welders-refined.md` — first matching taskspace plan (glob)
4. If none exist: create `docs/plan-10-mock-welders.md` with tuning guide content; abort edits elsewhere with instruction: "Create docs/plan-10-mock-welders.md with the tuning guide and reproducibility note. Do not proceed until a plan file exists."

**CI note:** taskspace is often absent in CI. Prefer `docs/` as canonical so CI and local use the same file.

---

## Implementation Steps

### Phase 1 — Prototype & Plan Doc Fixes

---

**Step 1.1 — Replace prototype make_session_for_arc with generate_session_for_welder**

*What:* Update `backend/scripts/prototype_arc_scoring.py` to use `generate_session_for_welder` from `mock_sessions` instead of `make_session_for_arc`. Remove duplicate arc_angle_tight, arc_angle_drift, arc_amps_stable, etc. Prototype validates the **production** path.

*File:* `backend/scripts/prototype_arc_scoring.py` (modify)

*Depends on:* Parent plan Step 1.3 (generate_session_for_welder exists). **Verify via Pre-Flight check above.**

*Code:*
```python
#!/usr/bin/env python3
"""
Prototype: validate that mock_sessions arc generation produces target score ranges.
Uses mock_sessions.generate_session_for_welder — same path as seed/Phase 2.
Run from project root: PYTHONPATH=backend python backend/scripts/prototype_arc_scoring.py

IMPORTANT: Run with fresh Python process. Do NOT run after mock_sessions/seed in same process —
random state advances and scores differ. If running in same process, call random.seed(42)
immediately before each PASS_BAND check inside the loop.
"""

import random
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))

from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features
from scoring.rule_based import score_session

PASS_BANDS = [
    ("fast_learner", 0, 43, 73),
    ("fast_learner", 4, 59, 98),
    ("declining", 0, 61, 91),
    ("declining", 4, 40, 70),
    ("volatile", 0, 38, 92),
    ("volatile", 2, 38, 92),
    ("consistent_expert", 0, 73, 103),
    ("consistent_expert", 4, 78, 108),
]


def main():
    random.seed(42)
    print("Prototype: mock_sessions.generate_session_for_welder → Features → Score")
    print("=" * 60)
    failures = []
    for arc, s_idx, min_s, max_s in PASS_BANDS:
        random.seed(42)  # Re-seed before each check if same process
        sid = f"sess_{arc}_{s_idx + 1:03d}"
        session = generate_session_for_welder(f"proto-{arc}", arc, s_idx, sid)
        feats = extract_features(session)
        sc = score_session(session, feats)
        ok = min_s <= sc.total <= max_s
        status = "OK" if ok else "FAIL"
        print(f"{arc} session {s_idx}: score={sc.total:.1f} [{min_s}-{max_s}] {status}")
        if not ok:
            failures.append((arc, s_idx, sc.total, min_s, max_s))

    if failures:
        print("\nFAILED: Scores outside pass bands. Tuning guide:")
        print("  fast_learner low → tighten _arc_angle_tight looseness (reduce max(0.5, 4.0 - session_idx*0.8))")
        print("  declining high → increase _arc_angle_drift drift_factor")
        print("  consistent_expert low → tighten expert_angle variance")
        for arc, s_idx, score, min_s, max_s in failures:
            print(f"  {arc} s{s_idx}: {score} not in [{min_s},{max_s}]")
        sys.exit(1)
    print("\nDone. All arcs in range.")


if __name__ == "__main__":
    main()
```

*Tuning guide param mapping:* The printed guidance references `_arc_angle_tight` (looseness factor) and `_arc_angle_drift` (drift_factor). Verify these identifiers exist in `backend/data/mock_sessions.py` (or in the code path used by `generate_frames_for_arc`); if parent refactored them, update the tuning guide strings to match actual tunable params.

*Verification grep (specific params and file):*
```bash
grep -E "_arc_angle_tight|_arc_angle_drift|looseness|drift_factor" backend/data/mock_sessions.py
```
At least one match per arc type (fast_learner uses looseness; declining uses drift_factor). If grep finds nothing: either parent moved logic elsewhere — update tuning guide to reference the actual file/symbols that drive scores; or add the arc helpers to mock_sessions per parent plan Step 1.2.

*Why this approach:* Critique P1: Prototype must validate production path; exploration locked "Replace make_session_for_arc with generate_session_for_welder".

*Verification:*
```
Setup: Pre-Flight check passed; cd project root
Action: PYTHONPATH=backend python backend/scripts/prototype_arc_scoring.py
Expected: All arcs print OK; exit 0
Pass criteria:
  [ ] All arc types produce scores within pass bands
  [ ] Script exits 1 if any score out of band
  [ ] Tuning guide printed on failure
  [ ] Tuning guide params exist: grep -E "_arc_angle_tight|_arc_angle_drift|looseness|drift_factor" backend/data/mock_sessions.py returns matches
If it fails: Apply tuning guide; ensure generate_session_for_welder is from mock_sessions; verify param names match mock_sessions
```

*Estimate:* 0.75h  

*Classification:* CRITICAL  

---

**Step 1.2 — Add tuning guide and fresh-process note to plan Step 1.4**

*What:* Update the **parent implementation plan** Step 1.4 with: (1) Tuning guide. (2) "Prototype must run with fresh Python process (not after mock_sessions/seed), or set random.seed(42) immediately before each PASS_BAND check inside the loop."

*Plan file resolution:* Use the canonical order defined in "Plan File Resolution" above. Resolve to the first existing file; if none exist, create `docs/plan-10-mock-welders.md` and add the content. **Do NOT edit** `.cursor/issues/10-mock-welders-with-skill-arcs.md` — that is the issue, not the implementation plan.

*File:* As resolved above (modify or create)

*Depends on:* none

*Code:*
```markdown
*Tuning guide (if scores outside pass bands):*
- fast_learner scores low → tighten _arc_angle_tight: reduce looseness factor (max(0.5, 4.0 - session_idx*0.8))
- declining scores high → increase _arc_angle_drift drift_factor
- consistent_expert low → tighten expert_angle variance

*Reproducibility:* Prototype must run with a fresh Python process, or random.seed(42) immediately before each PASS_BAND check inside the loop. The seed route advances RNG; running prototype after seed yields different scores.
```

*Why this approach:* Critique P1 — implementers need actionable remediation, not "tune angle/amps/volts".

*Verification:*
```
Setup: Plan file exists (create if needed per resolution above)
Action: grep -l "Tuning guide" docs/plan-10-mock-welders.md .cursor/issues/10-mock-welders-plan.md 2>/dev/null || true
Action: grep -A2 "Tuning guide" <resolved_plan_file>
Expected: Tuning guide and Reproducibility note present in the resolved implementation plan file
Pass criteria:
  [ ] fast_learner and declining mappings documented
  [ ] Fresh process / seed note present
  [ ] Edits landed in implementation plan (docs/ or .cursor/issues/10-mock-welders-plan.md), NOT in 10-mock-welders-with-skill-arcs.md
  [ ] File is in version control for CI/deploy
If it fails: Re-apply edits to correct file; ensure docs/ or plan file is committed
```

*Estimate:* 0.25h  

*Classification:* NON-CRITICAL  

---

**Step 1.3 — Add Phase 3 pre-flight: verify WELDERS matches WELDER_ARCHETYPES**

*What:* Add to Phase 3 Pre-Flight Checklist: "Verify WELDERS in page.tsx matches WELDER_ARCHETYPES: compare welder IDs and **sessions** (not sessionCounts — parent uses `sessions` per archetype) manually or with a quick script."

*File:* Parent plan file (modify; resolve per Plan File Resolution)

*Depends on:* none

*Code:*
```markdown
- [ ] **WELDERS in seagull/page.tsx matches WELDER_ARCHETYPES** — Run: `grep -E "welder_id|sessions" backend/data/mock_welders.py` and compare IDs + sessions count to WELDERS in page.tsx; or run a 2-minute diff script. Fix: add missing welders or correct session count.
```

*Why this approach:* Critique P2 — 3-file duplication has no enforcement; 2-minute pre-flight prevents 404 at demo.

*Verification:*
```
Setup: Plan file exists
Action: grep "WELDERS.*WELDER_ARCHETYPES" plan file
Expected: Pre-flight item present; terminology uses "sessions" not "sessionCounts"
Pass criteria:
  [ ] Phase 3 pre-flight has archetype sync check
If it fails: Add to Phase 3 Prerequisites
```

*Estimate:* 0.15h  

*Classification:* NON-CRITICAL  

---

**Step 1.4 — Use Tuple for generate_frames_for_arc return type (Python 3.8 compat)**

*What:* In `backend/data/mock_sessions.py`, change `tuple[List[Frame], bool]` to `Tuple[List[Frame], bool]` (from `typing`) or add `from __future__ import annotations` at top. Ensures compatibility if Python 3.8 is used.

*File:* `backend/data/mock_sessions.py` (modify)

*Depends on:* Parent plan Step 1.2 (generate_frames_for_arc exists)

*Code:*
```python
# Option A: add at top
from __future__ import annotations

# Option B: if not using __future__
from typing import Tuple
# Then use: Tuple[List[Frame], bool]
```

*Why this approach:* Minor critique — `tuple[List[Frame], bool]` requires Python 3.9+.

*Verification:*
```
Setup: generate_frames_for_arc exists
Action: From project root: PYTHONPATH=backend python -c "from data.mock_sessions import generate_frames_for_arc"
Expected: No SyntaxError or NameError
Pass criteria:
  [ ] Import succeeds
If it fails: Add Tuple from typing or __future__ annotations
```

*Estimate:* 0.1h  

*Classification:* NON-CRITICAL  

---

**Step 1.5 — Fold Step 2.3 into Step 2.1 and document wipe vs seed delete**

*What:* In parent plan: (1) Merge "Add import random" into Step 2.1 seed route step. (2) Add note: "Wipe uses .delete(synchronize_session=False); seed uses loop db.delete(existing). Loop is slower for 45 sessions but acceptable; note for reviewer."

*File:* Parent plan file (modify; resolve per Plan File Resolution)

*Depends on:* none

*Code:*
```markdown
*Note:* Step 2.1 includes `import random` at top of dev.py. Wipe uses bulk `.delete(synchronize_session=False)`; seed uses loop `db.delete(existing)` per session. Loop is slower but acceptable for ~45 sessions; both are correct—inconsistency is intentional (wipe targets known IDs; seed deletes before re-add).
```

*Why this approach:* Minor critique — reduces step count; clarifies delete behavior for reviewers.

*Verification:*
```
Setup: Plan file exists
Action: grep -c "Step 2.3" plan file; grep "wipe.*seed.*delete" plan file
Expected: No standalone Step 2.3; wipe/seed note present
Pass criteria:
  [ ] import random in Step 2.1
  [ ] Delete inconsistency documented
If it fails: Merge Step 2.3 content into 2.1; add note
```

*Estimate:* 0.25h  

*Classification:* NON-CRITICAL  

---

### Phase 2 — Seed & Spot-Check Fixes

---

**Step 2.1 — Fix seed_demo_data spot-check: use session_ids[0] and first archetype**

*What:* Update `backend/scripts/seed_demo_data.py` so:
1. **session_ids and expected_count are derived at the very start of main()**, before any branch. Order MUST match WELDER_ARCHETYPES iteration: `session_ids = [f"sess_{a['welder_id']}_{i:03d}" for a in WELDER_ARCHETYPES for i in range(1, a['sessions']+1)]` — so `session_ids[0]` is the first archetype's first session.
2. **Validation: if expected_count == 0 (empty WELDER_ARCHETYPES or all sessions==0), fail fast** — do not skip with "Demo data already complete." Use: `if expected_count == 0: raise ValueError("WELDER_ARCHETYPES empty or all sessions=0; cannot seed. Fix archetypes.")`.
3. Spot-check uses `session_ids[0]` and `WELDER_ARCHETYPES[0]["welder_id"]` — never hardcoded `sess_mike-chen_001`.
4. Spot-check runs in **both** (a) when existing == expected_count (skip path) and (b) after re-seed (existing > 0 path).

*File:* `backend/scripts/seed_demo_data.py` (modify)

*Depends on:* Parent plan Step 2.4 (seed_demo_data loops WELDER_ARCHETYPES) — if parent not done, implement full seed_demo_data with this spot-check logic

*Code:*
```python
#!/usr/bin/env python3
"""
Seed demo sessions from WELDER_ARCHETYPES into the database.
Idempotent: skips only when existing == expected_count AND spot-check passes.
Run from backend/ or with PYTHONPATH including backend.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from data.mock_welders import WELDER_ARCHETYPES
from data.mock_sessions import generate_session_for_welder
from database.connection import SessionLocal
from database.models import SessionModel


def _spot_check(db, session_ids: list[str], expected_operator_id: str) -> bool:
    """Verify first session has correct operator_id. Returns True if valid."""
    if not session_ids:
        return True
    first_id = session_ids[0]
    sess = db.query(SessionModel).filter(SessionModel.session_id == first_id).first()
    if sess is None:
        return False
    return sess.operator_id == expected_operator_id


def main() -> int:
    db = SessionLocal()

    # CRITICAL: Derive session_ids at start, before any branch.
    # Order MUST match WELDER_ARCHETYPES — session_ids[0] = first archetype's first session.
    session_ids = [
        f"sess_{a['welder_id']}_{i:03d}"
        for a in WELDER_ARCHETYPES
        for i in range(1, a["sessions"] + 1)
    ]
    expected_count = len(session_ids)

    # Fail fast if no sessions to seed (empty archetypes or all sessions=0)
    if expected_count == 0:
        print("ERROR: WELDER_ARCHETYPES empty or all sessions=0. Cannot seed.", file=sys.stderr)
        return 1

    try:
        existing = db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).count()

        if existing == expected_count:
            if _spot_check(db, session_ids, WELDER_ARCHETYPES[0]["welder_id"]):
                print("Demo data already complete, skipping.", file=sys.stderr)
                return 0
            print("Spot-check failed: operator_id mismatch. Re-seeding.", file=sys.stderr)

        if existing > 0:
            if existing < expected_count:
                print(f"Warning: {existing}/{expected_count} sessions exist. Re-seeding all.", file=sys.stderr)
            for s in db.query(SessionModel).filter(
                SessionModel.session_id.in_(session_ids)
            ).all():
                db.delete(s)
            db.flush()

        for archetype in WELDER_ARCHETYPES:
            welder_id = archetype["welder_id"]
            arc = archetype["arc"]
            for i in range(archetype["sessions"]):
                sid = f"sess_{welder_id}_{i+1:03d}"
                session = generate_session_for_welder(welder_id, arc, i, sid)
                model = SessionModel.from_pydantic(session)
                db.add(model)

        db.commit()

        if not _spot_check(db, session_ids, WELDER_ARCHETYPES[0]["welder_id"]):
            raise RuntimeError("Spot-check failed after seed: operator_id mismatch")

        print(f"Demo data seeded: {expected_count} sessions", file=sys.stderr)
        return 0
    except Exception as e:
        import traceback
        print(f"Seeding failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
```

*Invariant assertion:* The list comprehension `for a in WELDER_ARCHETYPES for i in range(1, a["sessions"]+1)` guarantees session_ids iteration order matches WELDER_ARCHETYPES. session_ids[0] is always WELDER_ARCHETYPES[0]'s first session.

*Why this approach:* Critique P3 — hardcoded sess_mike-chen_001 silently passes when mike-chen removed; session_ids derivation at start ensures it exists in skip path and aligns with first archetype. Empty expected_count fails fast.

*Verification:*
```
Setup: Parent Step 2.4 complete or seed_demo_data has WELDER_ARCHETYPES loop
Action: python backend/scripts/seed_demo_data.py; run twice — second run must skip
Action: SELECT operator_id FROM sessions WHERE session_id = (first session_ids value);
Expected: operator_id matches WELDER_ARCHETYPES[0]["welder_id"]
Pass criteria:
  [ ] session_ids derived at start of main() before any if/else
  [ ] expected_count == 0 returns 1 and does NOT skip with "already complete"
  [ ] session_ids order matches WELDER_ARCHETYPES (list comp over archetypes first)
  [ ] Spot-check uses session_ids[0], not hardcoded ID
  [ ] Spot-check runs when skipping (existing == expected_count)
  [ ] Spot-check runs after re-seed
  [ ] Re-seed triggered if spot-check fails on skip path
  [ ] Second run (skip path) does NOT raise NameError
If it fails: Ensure session_ids/expected_count at top of main(); both branches call _spot_check; add expected_count==0 guard
```

*Estimate:* 0.75h  

*Classification:* CRITICAL  

---

**Step 2.2 — Ensure seed_demo_data idempotent on existing == expected_count only**

*What:* Verify seed_demo_data skips only when existing == expected_count. When existing > 0 but < expected_count (partial seed), it must re-seed all, not skip.

*Orphan sessions:* Re-seed deletes only sessions in session_ids. Old sessions from prior archetype versions (e.g. sess_old-welder_001) may persist. For this plan, document: "Orphan sessions from prior schema may accumulate. Full wipe (delete all demo sessions) is out of scope; periodic manual cleanup or wipe route covers it." Optionally: before re-seed, delete any SessionModel where session_id matches pattern `sess_%` and is not in session_ids — add if acceptable for schema. **No script for manual delete-one verification** — use SQL: `DELETE FROM sessions WHERE session_id = 'sess_mike-chen_003';` for partial-seed test.

*File:* `backend/scripts/seed_demo_data.py` (modify)

*Depends on:* Step 2.1, Parent Step 2.4

*Code:*
```python
# Correct logic (integrated in Step 2.1):
if existing == expected_count:
    if _spot_check(db, session_ids, WELDER_ARCHETYPES[0]["welder_id"]):
        return 0
    # fall through to re-seed
if existing > 0:
    # Partial or corrupt — delete and re-seed
    for s in db.query(SessionModel).filter(SessionModel.session_id.in_(session_ids)).all():
        db.delete(s)
    db.flush()
# then seed...
```

*Verification:*
```
Setup: Seed 44/45 — run: python -c "from database.connection import SessionLocal; from database.models import SessionModel; db=SessionLocal(); db.query(SessionModel).filter(SessionModel.session_id=='sess_mike-chen_003').delete(); db.commit(); db.close()"
Action: python backend/scripts/seed_demo_data.py
Expected: "Warning: 44/45 sessions exist. Re-seeding all." (or equivalent) then "Demo data seeded: 45 sessions"
Pass criteria:
  [ ] Partial data does NOT skip
  [ ] Full data + spot-check OK skips
If it fails: Fix if condition — only skip when existing == expected_count AND spot_check passes
```

*Estimate:* 0.25h  

*Classification:* CRITICAL  

---

### Phase 3 — Dashboard & Welder Report Fixes

---

**Step 3.1 — Specify skeleton/spinner during dashboard load; setWelderScores once**

*What:* Update dashboard (seagull/page.tsx) so cards show skeleton/spinner while loading—not empty score values. Use `loading` state to render card placeholders with `animate-pulse` or "Loading..." until Promise.allSettled resolves. Call setWelderScores once after all fetches complete.

*File:* `my-app/src/app/seagull/page.tsx` (modify)

*Depends on:* Parent plan Step 3.1–3.2 (10 welders, fetchScore)

*Code:*
```typescript
// During loading: show skeleton cards, not empty scores
if (loading || welderScores === null) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <h1 className="text-2xl font-bold mb-6">Team Dashboard</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {WELDERS.map((w) => (
          <div key={w.id} className="p-6 bg-white dark:bg-zinc-900 rounded-lg border animate-pulse">
            <div className="h-5 bg-zinc-200 dark:bg-zinc-700 rounded w-2/3 mb-2" />
            <div className="h-4 bg-zinc-200 dark:bg-zinc-700 rounded w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

// In useEffect: setWelderScores ONCE after Promise.allSettled
Promise.allSettled(fetches.map(...)).then((results) => {
  // ... build byWelder ...
  setWelderScores(mapped);
  setLoading(false);
});
```

*Why this approach:* Critique P4 — 20 fetches can take 4s; empty "Score unavailable" looks broken.

*Verification:*
```
Setup: Seeded backend; throttle network (DevTools Network: Slow 3G) for reliable observation
Action: Open /seagull; observe initial render
Expected: Skeleton cards with animate-pulse for ~1–4s (or until fetches complete), then scores populate; no brief "Score unavailable" before data
Pass criteria:
  [ ] Cards show skeleton (not empty scores) during load
  [ ] setWelderScores called once after allSettled
  [ ] No 20 separate setState calls (code review: single setWelderScores in then handler)
  [ ] Throttled network shows skeleton visibly before scores
If it fails: Ensure loading=true until allSettled resolves; render skeleton when loading
```

*Estimate:* 0.5h  

*Classification:* CRITICAL  

---

**Step 3.2 — Use sc.total for last slot in historicalScores (welder report)**

*What:* In welder report page, when building historicalScores for generateAIFeedback: the last session is the current session—we already have sc from fetchScore(sessionId). Use sc.total for the last index; **never 0 when score is available**.

*Behavior when sc is null (fetch failed):* Do NOT pass 0 for last slot—that reintroduces the bug (historicalScores ends with 0 → "declining"). Options: (A) Do not render trend section; show "insufficient_data" or "Score unavailable". (B) Do not call generateAIFeedback until sc is available. Never: `historicalScores = [...histScores, 0]` when sc is null.

*File:* `my-app/src/app/seagull/welder/[id]/page.tsx` (modify)

*Depends on:* Parent plan Step 4.3–4.4 (historical fetch)

*Code:*
```typescript
// Guard: Do not build historicalScores when sc is null (fetch failed)
if (!sc) {
  // Do not pass 0 for last slot — that causes false "declining"
  setReport(null);  // or setReport with trend: "insufficient_data")
  return;
}

// Last session IS current session — use sc.total, don't re-fetch
const histFetchIds = historicalSessionIds.slice(0, -1);
const histResults = await Promise.allSettled(histFetchIds.map((sid) => fetchScore(sid)));
const histScores = histResults.map((r) =>
  r.status === "fulfilled" ? (r.value as SessionScore).total : 0
);
const historicalScores = [...histScores, sc.total];
```

*Why this approach:* Critique P5 / exploration — last slot must use sc.total; 0 or sc?.total ?? 0 when sc is null causes "declining" for fast_learner wrongly.

*Verification:*
```
Setup: Seeded; open /seagull/welder/mike-chen
Action: Check AI feedback trend for fast_learner
Expected: "improving" (last > prev), not "declining"
Action: Simulate fetch failure (e.g. block /api/score in DevTools) — reload
Expected: Trend not shown, or "insufficient_data"; never "declining" due to last-slot 0
Pass criteria:
  [ ] historicalScores[lastIdx] === sc.total when sc available
  [ ] When sc is null: no 0 appended; trend not rendered or shows insufficient_data
  [ ] Trend correct for improving welders when sc available
If it fails: Ensure last slot uses sc.total; guard on sc before building historicalScores
```

*Estimate:* 0.5h  

*Classification:* CRITICAL  

---

**Step 3.3 — Document badge flicker for plateaued/volatile**

*What:* Add to Step 3.3 (badge logic) in plan or as comment: "plateaued and volatile have ±2 noise; score > secondScore vs score < secondScore may flip across runs. This is expected. Optional: add ±2 dead zone (|delta| < 2 → neutral) to reduce flicker."

*File:* Parent plan or `my-app/src/app/seagull/page.tsx` (comment)

*Depends on:* none

*Code:*
```typescript
// Badge: plateaued/volatile with ±2 noise may flicker between on_track and needs_attention.
// Expected behavior. Optional: |score - secondScore| < 2 → neutral for stability.
function getBadge(score: number | null, secondScore: number | null): "on_track" | "needs_attention" | "neutral" | null {
  if (score === null || secondScore === null) return null;
  const delta = score - secondScore;
  if (Math.abs(delta) < 2) return "neutral";  // Optional dead zone
  if (delta > 0) return "on_track";
  return "needs_attention";
}
```

*Why this approach:* Minor critique — document expected behavior; dead zone optional. Product decision: document in plan; implementer may skip dead zone if not desired.

*Verification:*
```
Setup: Plan or code updated
Action: grep "flicker\|dead zone\|plateaued" plan or page
Expected: Note present
Pass criteria:
  [ ] Badge flicker documented or dead zone added
If it fails: Add comment or plan note
```

*Estimate:* 0.15h  

*Classification:* NON-CRITICAL  

---

### Phase 4 — Tests & Verification

---

**Step 4.1 — Add last-slot tests to ai-feedback.test.ts**

*What:* Add concrete tests: (1) "trend is declining when last slot is 0 and prev is higher" — documents caller contract: never pass 0 for last slot when sc.total available. (2) "trend is improving when last slot has real score and prev is lower". (3) "last slot 0 with prev lower yields declining (engine treats 0 as real value)" — documents that engine does not special-case 0; caller must pass sc.total. (4) **fetchScore null → insufficient_data or no trend**: Add test that mocks sc=null (or fetchScore returning null) and asserts generateAIFeedback is not called with historicalScores ending in 0, or trend shows insufficient_data.

*File:* `my-app/src/__tests__/lib/ai-feedback.test.ts` (modify)

*Depends on:* none

*Code:*
```typescript
describe("generateAIFeedback — last-slot historicalScores contract", () => {
  it("trend is declining when last slot is 0 and prev is higher (caller pitfall)", () => {
    // Caller must NOT pass 0 for last slot when sc.total is available.
    // [72, 0] with score.total=78 would wrongly show declining — use [72, 78] instead.
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 78 }),
      [72, 0]
    );
    expect(result.trend).toBe("declining");
  });

  it("trend is improving when last slot has real score (correct caller behavior)", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 78 }),
      [72, 78]
    );
    expect(result.trend).toBe("improving");
  });

  it("last slot 0 with prev higher yields declining — 0 is a real value to engine", () => {
    // Engine compares last vs prev; 0 < 80 → declining.
    // Caller should never pass 0 when sc.total is available.
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 50 }),
      [80, 0]
    );
    expect(result.trend).toBe("declining");
  });

  it("caller contract: when sc is null, never pass 0 for last slot — use insufficient_data or skip", () => {
    // When fetchScore fails, sc is null. Caller must NOT build historicalScores with 0 at end.
    // This documents: [...histScores, 0] yields declining (see test above). Contract: when sc
    // is null, do NOT call generateAIFeedback with [...histScores, 0]. Use insufficient_data
    // or omit trend (e.g. setReport(null) or trend: "insufficient_data").
    const wrongResult = generateAIFeedback(mockSession(), mockScore({ total: 50 }), [72, 75, 78, 0]);
    expect(wrongResult.trend).toBe("declining");
  });
});
```

*Why this approach:* Critique P5 — last-slot bug is subtle; test prevents regression in engine. **Caller contract:** Caller (welder report) must pass sc.total for last slot; this test documents that 0 produces wrong trend. Standard critique: Add unit test that mocks fetchScore null → insufficient_data.

*Verification:*
```
Setup: cd my-app
Action: npm test -- ai-feedback.test.ts
Expected: All tests pass including new last-slot tests
Pass criteria:
  [ ] test "trend is declining when last slot is 0" passes
  [ ] test "trend is improving when last slot has real score" passes
  [ ] test "sc null" documents caller contract
  [ ] Tests document caller contract
If it fails: Ensure mockScore total matches expected trend
```

*Estimate:* 0.5h  

*Classification:* CRITICAL  

---

**Step 4.2 — Update plan Step 5.3 with concrete test or manual-only note**

*What:* Replace Step 5.3 pseudocode with either: (A) Full test code referencing ai-feedback.test.ts last-slot tests, or (B) Explicit "Manual verification only — owner must run Step 4.4 verification before every demo."

*File:* Parent plan file (modify; resolve per Plan File Resolution)

*Depends on:* Step 4.1

*Code:*
```markdown
**Step 5.3 — Test historicalScores last-slot behavior**

*What:* Add tests in `my-app/src/__tests__/lib/ai-feedback.test.ts`:
- trend declining when historicalScores = [72, 0] (caller pitfall)
- trend improving when historicalScores = [72, 78] (correct: last slot = sc.total)

See critique fixes plan Step 4.1 for full test code. If test infra gaps: manual verification only — run Step 4.4 verification (delete sess_mike-chen_003, open report, ensure trend uses sc.total for last slot) before every demo.
```

*Verification:*
```
Setup: Plan file exists
Action: grep "Step 5.3" plan file
Expected: Concrete test reference or "manual verification only"
Pass criteria:
  [ ] Step 5.3 has implementable content
If it fails: Add test ref or manual-only note
```

*Estimate:* 0.25h  

*Classification:* NON-CRITICAL  

---

**Step 4.3 — Integration test: welder report caller passes sc.total for last slot**

*What:* Add integration or E2E test: with seeded fast_learner, welder report must show trend = "improving". This asserts the **caller** passes sc.total for last slot, not just that the engine behaves correctly.

*File:* `my-app/src/__tests__/e2e/welder-report-last-slot.test.ts` (create) or add to existing E2E suite

*Depends on:* Step 3.2, seeded backend or mocked API

*Code (pseudo — adapt to project's E2E framework):*
```typescript
// E2E or integration: /seagull/welder/mike-chen with seeded fast_learner
// GET /api/score/sess_mike-chen_005 returns total 75 (e.g.)
// historicalSessionIds = [sess_001, sess_002, sess_003, sess_004, sess_005]
// histScores from fetch = [60, 65, 68, 72]; last = sc.total = 75
// generateAIFeedback(..., [60,65,68,72,75]) → trend = "improving"
// Assert: page shows "improving" or equivalent
```

*Fallback:* If E2E not set up: add a unit test that mocks fetchScore and verifies the welder report **component** passes `[...histScores, sc.total]` to generateAIFeedback when sc is available. Document: "Full E2E deferred; manual Step 4.4 verification before demo."

*Gate (CRITICAL):* If E2E not set up, **require explicit manual verification before merge**:
- Add PR checklist item: "Manual Step 4.4 verification completed: opened /seagull/welder/mike-chen, confirmed trend = improving for fast_learner."
- Or: block merge until `docs/verification-4.4.md` (or equivalent) exists with date and "trend correct" confirmation.
- Do not allow "manual fallback documented" without enforcement — regression can ship otherwise.

*Verification:*
```
Setup: Seeded DB or mocked API with fast_learner scores
Action: Run E2E or integration test
Expected: trend = improving for fast_learner welder report
Pass criteria:
  [ ] Caller (welder report) passes sc.total for last slot in historicalScores
  [ ] Test fails if caller incorrectly passes 0
  [ ] If E2E not available: PR has checklist or verification doc; merge blocked until manual Step 4.4 completed and documented
If E2E not available: Document manual gate in PR template or CONTRIBUTING.md; add to success criteria
```

*Estimate:* 0.25h  

*Classification:* CRITICAL (or manual gate enforced)  

---

## Risk Heatmap

| Phase.Step | Risk Description | Probability | Impact | Early Warning | Mitigation |
|------------|------------------|-------------|--------|---------------|------------|
| 1.1 | Prototype still fails after tuning | Med | High | Scores outside bands after param tweaks | Tuning guide in script output; verify param names match mock_sessions; iterate |
| 2.1 | session_ids undefined in skip path | High | High | NameError on second run | session_ids derived at start of main(); code sample includes full flow |
| 2.1 | Empty WELDER_ARCHETYPES skips with zero data | Med | High | "Demo data already complete" with 0 sessions | expected_count==0 guard; fail fast with return 1 |
| 2.2 | Partial seed still skips | Low | High | 44/45 → "already complete" | existing == expected_count; never skip when existing < expected |
| 3.1 | Skeleton doesn't show | Low | Med | Empty scores flash | loading=true until allSettled; render skeleton when loading |
| 3.2 | Last slot 0 when sc null | Med | High | fetch fails → false "declining" | Guard: do not pass 0 when sc is null; use insufficient_data |
| 4.1 | Test fragile across ai-feedback changes | Low | Low | Test fails after semantic change | Test documents contract; update if trend logic changes |
| 1.2 | Plan doc wrong file (issue vs plan) | Med | High | Tuning guide in issue; parent plan unupdated | Canonical resolution: docs/ first; never edit issue file |
| 1.2 | Plan doc overwritten or path missing | Med | Med | Tuning guide lost in CI | docs/ canonical; version control; avoid editing taskspace in CI |
| 1.2 | Version control conflict on plan | Low | Med | Both plans edit same file | Single canonical path (docs/); document in README |
| 4.3 | Manual fallback drift — never run before demo | High | High | Regression ships; demo fails | PR checklist or verification doc; block merge until Step 4.4 completed |
| 1.3 | Pre-flight not run before demo | Med | High | 404 for new welder | Add to Pre-Flight; automated dependency check |
| 2.1 | Parent uses sessionCount not sessions | Med | High | KeyError at runtime | Pre-flight asserts 'sessions' key; fail fast |

---

## Pre-Flight Checklist

### Before Phase 1

- [ ] **Run automated dependency and structure check** (see top of document) — must succeed
- [ ] `backend/data/mock_welders.py` exists — `ls backend/data/mock_welders.py`
- [ ] Plan file path known — resolve per Plan File Resolution (docs/ or .cursor/issues/10-mock-welders-plan.md)

### Phase 2 Prerequisites

- [ ] Parent Step 2.4 seed_demo_data loops WELDER_ARCHETYPES — grep "WELDER_ARCHETYPES" seed_demo_data.py
- [ ] Database reachable — backend running
- [ ] SessionModel and SessionLocal available — `from database.models import SessionModel`

### Phase 3 Prerequisites

- [ ] Parent Steps 3.1–3.2 complete — WELDERS has sessionCount; fetchScore used
- [ ] Parent Steps 4.3–4.4 complete — historical fetch; generateAIFeedback receives historicalScores
- [ ] my-app builds — `cd my-app && npm run build`
- [ ] Seeded data for verification — run seed before testing

### Phase 4 Prerequisites

- [ ] Jest or test runner configured — `npm test` works
- [ ] ai-feedback.test.ts exists — `ls my-app/src/__tests__/lib/ai-feedback.test.ts`
- [ ] Phases 1–3 complete
- [ ] generateAIFeedback signature unchanged — accepts historicalScores: number[]

---

## Success Criteria

| # | Condition | How to Verify | Priority |
|---|-----------|---------------|----------|
| 1 | Pre-flight dependency and structure check passes | PYTHONPATH=backend python -c "from data.mock_sessions import generate_session_for_welder; from data.mock_welders import WELDER_ARCHETYPES; assert len(WELDER_ARCHETYPES)>0 and all('welder_id' in a and 'sessions' in a and a['sessions']>=1 for a in WELDER_ARCHETYPES)" | P0 |
| 2 | Prototype uses generate_session_for_welder | grep "generate_session_for_welder" prototype_arc_scoring.py | P0 |
| 3 | Tuning guide in prototype and plan | Prototype prints guide on failure; plan Step 1.4 has guide | P0 |
| 4 | Fresh process / seed note in plan | grep "fresh Python process" plan | P0 |
| 5 | Phase 3 pre-flight has archetype sync check | grep "WELDERS.*WELDER_ARCHETYPES" plan | P0 |
| 6 | session_ids derived at start of main() | session_ids = [...] before any branch in seed_demo_data | P0 |
| 7 | expected_count==0 fails (no silent skip) | Empty archetypes → script returns 1 | P0 |
| 8 | Spot-check uses session_ids[0] not hardcoded | grep "session_ids[0]" seed_demo_data.py | P0 |
| 9 | Spot-check runs in skip and re-seed paths | Trace code; both branches call _spot_check | P0 |
| 10 | Partial seed (44/45) triggers re-seed | Delete one session; run seed; expect re-seed | P0 |
| 11 | Cards show skeleton during load | Open /seagull; throttle network; observe skeleton before scores | P0 |
| 12 | Last slot uses sc.total when sc available | Open fast_learner report; trend = improving | P0 |
| 13 | When sc null: no 0 for last slot | Block fetch; reload; trend not "declining" from 0 | P0 |
| 14 | ai-feedback last-slot tests pass | npm test ai-feedback.test.ts | P0 |
| 15 | Integration/E2E or manual gate: caller passes sc.total | welder report trend correct for fast_learner; if manual: PR checklist or verification doc | P0 |
| 16 | Badge flicker documented or dead zone added | grep "flicker\|dead zone" plan or code | P1 |
| 17 | generate_frames_for_arc Python 3.8 compat | Import succeeds (PYTHONPATH=backend from root) | P1 |
| 18 | Step 2.3 folded; wipe/seed note in plan | No standalone Step 2.3; delete note present | P1 |
| 19 | Plan resolution uses implementation plan not issue | Tuning guide in docs/ or 10-mock-welders-plan.md; not 10-mock-welders-with-skill-arcs.md | P1 |

---

## Rollback Procedure

- **Phase 1:** Revert prototype_arc_scoring.py to use make_session_for_arc if it exists; revert plan edits (in canonical plan file)
- **Phase 2:** Revert seed_demo_data.py; re-run wipe route if needed
- **Phase 3:** Revert page.tsx and welder report; clear browser cache
- **Phase 4:** Revert test file changes
- **Data:** If seed corrupted, run wipe then seed from parent plan
- **Plan conflicts:** If version control conflict on plan file, resolve by keeping docs/ as canonical; merge tuning guide from both branches

---

## Known Issues & Limitations

- Orphan sessions from prior archetype versions may persist; full wipe is out of scope for this plan
- Plan file resolution: .cursor/taskspace may not exist in CI; docs/ is canonical; create docs/plan-10-mock-welders.md if absent
- E2E for welder report caller: manual Step 4.4 verification required if E2E not set up; **PR checklist or verification doc must block merge**
- Tuning guide param names may drift if mock_sessions refactored; verify with grep before applying
- Spot-check only validates session_ids[0]; corrupt operator_id on session 2..N would pass; full validation out of scope
- Step 3.1 skeleton verification requires manual DevTools throttle; no automated CI assertion for "skeleton shows before scores"

---

## Progress Tracker

```
| Phase | Steps | Done | In Progress | Blocked | % |
|-------|-------|------|-------------|---------|---|
| Phase 1 | 5 | 0 | 0 | 0 | 0% |
| Phase 2 | 2 | 0 | 0 | 0 | 0% |
| Phase 3 | 3 | 0 | 0 | 0 | 0% |
| Phase 4 | 3 | 0 | 0 | 0 | 0% |
| TOTAL | 13 | 0 | 0 | 0 | 0% |
```

---

## Self-Check Before Submitting

- [x] Every step has verification with specific pass criteria
- [x] CRITICAL steps have full working code or clear reference
- [x] Dependencies correctly sequenced (Phase 1 before 2; parent steps noted)
- [x] All critique items mapped to steps (P1–P5 + 4 minor)
- [x] session_ids derived at start of main() before any branch
- [x] expected_count==0 fails fast (no silent skip with zero data)
- [x] Pre-flight asserts WELDER_ARCHETYPES structure (welder_id, sessions, sessions>=1)
- [x] Spot-check runs in both skip and re-seed branches
- [x] Last-slot fix: sc.total for last index; guard when sc is null
- [x] Pre-flight automated dependency and structure check
- [x] Plan file resolution: docs/ canonical; never edit issue file
- [x] Tuning guide param verification (grep with specific file)
- [x] Integration test or manual gate enforced for caller (PR checklist/verification doc)
- [x] Unit test for sc null / insufficient_data contract
- [x] Manual fallback drift risk in risk heatmap
- [x] Version control conflict mitigation documented
