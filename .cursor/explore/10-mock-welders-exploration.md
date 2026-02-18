# Exploration: 10 Mock Welders With Skill Arcs

**Issue:** 10-mock-welders-with-skill-arcs  
**Date:** 2026-02-18  
**Explorer:** Technical exploration for planning handoff  

---

## 1. Complexity Classification

**State: Moderate**

Justification: Reuses existing mock session infrastructure, seed/wipe routes, dashboard, and welder report. The main effort is arc-aware frame generation (tuning ~6 arc types to hit score ranges) and coordinating session IDs across frontend/backend. No new APIs, no schema changes, no ML. Risk is bounded by deterministic scoring and `random.seed()` for reproducibility.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | Low | Mock data only; wipe is explicit; no production tables touched |
| Service disruption risk | Low | Dev-only seed/wipe; existing routes unchanged; new code is additive |
| Security risk | Low | No new endpoints; seed/wipe remain dev-gated |
| Dependency risk | Low | No new packages; uses existing mock_sessions, extractor, scoring |
| Rollback complexity | Low | Revert mock_welders + dev route changes; re-seed previous 2-session state |

---

## 3. Codebase Findings

Searched the codebase for mock sessions, seed/wipe, dashboard, welder report, scoring, and frame generation.

| File | What it does | Pattern | Reuse | Avoid |
|------|--------------|---------|-------|-------|
| `backend/data/mock_sessions.py` | `generate_expert_session`, `generate_novice_session`, `generate_frames`, signal generators | Physics-driven frames: angle → thermal asymmetry, amps/volts → center temp | Reuse `generate_frames`, `generate_thermal_snapshots`, THERMAL_* constants | Don't bypass physics; ensure angle/amps/volts stay causal |
| `backend/routes/dev.py` | `POST /seed-mock-sessions`, `POST /wipe-mock-sessions` | Delete-by-ID then insert; dev-gated | Extend session_ids from WELDER_ARCHETYPES; same delete-then-insert flow | Don't forget to extend wipe ID list |
| `backend/scripts/seed_demo_data.py` | CLI seed for sess_expert_001, sess_novice_001 | Idempotent (skip if exists) | Mirror or call shared generator; keep idempotent | Don't diverge from API seed logic |
| `my-app/src/app/seagull/page.tsx` | Dashboard: WELDERS array, `Promise.allSettled(fetchScore)` | 2 welders, 1 sessionId each | Expand to 10 welders; add sessionCount; derive latestSessionId = `sess_${id}_${pad(n)}`; add badge logic | Don't hardcode session IDs per welder if derivable |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Welder report: WELDER_MAP, MOCK_HISTORICAL, expert comparison | Hardcoded sess_expert_001, [68,72,75] | Use expert-benchmark's latest (`sess_expert-benchmark_005`); replace MOCK_HISTORICAL with `Promise.all(fetchScore(...))` for sess_xxx_001..00n | Don't keep MOCK_HISTORICAL |
| `backend/features/extractor.py` | 5 features: amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range | Pure function Session → dict | Used by score; frame params must drive these | N/A |
| `backend/scoring/rule_based.py` | 5 rules × 20 = total 0–100 | Each rule: actual <= threshold → pass | Thresholds fixed; tune frames to hit target scores | Don't change thresholds for mock |
| `my-app/src/lib/ai-feedback.ts` | `generateAIFeedback(session, score, historicalScores)` | Trend from last 2 of historicalScores | Pass real fetched scores; trend logic is improving/declining/stable | historicalScores in chronological order |
| `my-app/src/lib/demo-config.ts` | `DEMO_WELDERS` (2 entries) | Used by /demo/team path | Seagull path uses its own WELDERS; demo-config is separate | Don't conflate Seagull WELDERS with DEMO_WELDERS |
| `backend/database/models.py` | `SessionModel`, `operator_id` indexed | operator_id = welder slug | Use operator_id = welder_id (e.g. mike-chen) | No new columns |
| `backend/tests/test_mock_sessions.py` | Validates expert/novice continuity, heat_diss | disable_sensor_continuity_checks for novice | Extend tests for arc sessions; volatile/declining may need continuity disabled | Match test expectations to arc behavior |

**Closest existing implementations (3+):**

1. **Expert/novice sessions** (`mock_sessions.py`): Two fixed profiles; we extend with 6 arc types parameterized by session_index.
2. **Seed/wipe** (`dev.py`): Two hardcoded IDs; we derive ~45 IDs from archetypes as single source of truth.
3. **Dashboard + Promise.allSettled** (`seagull/page.tsx`): Already fetches scores per welder; we add badge derivation from last 2 scores.
4. **Welder report** (`welder/[id]/page.tsx`): Uses WELDER_MAP + MOCK_HISTORICAL; we replace with dynamic session list and fetched scores.

**Gap:** No arc-specific frame generation. Current code has expert/novice only. We must add `generate_frames_for_arc(arc_type, session_index)` that returns frames (or Session) with angle/amps/thermal profiles tuned per arc.

---

## 4. Known Constraints

- **Locked dependencies:** None new; use existing stack.
- **Framework rules:** Next.js client components; hooks run unconditionally; `params` can be Promise (Suspense).
- **Performance:** Dashboard will do up to 20 `fetchScore` calls (10 welders × 2 for badge). Acceptable with `Promise.allSettled`. Welder report: up to 5 `fetchScore` + 2 `fetchSession` per visit.
- **Reference stability:** WELDERS array is constant; no parent re-render replacing refs.
- **Scoring:** Deterministic; `extract_features` + `score_session`; no stored scores on frames—scores computed on demand.
- **Validation:** Sessions must pass `Session.validate_*`; `disable_sensor_continuity_checks=True` required for volatile/declining arcs (large amps/angle swings).
- **Session ID format:** `sess_{welder_id}_{001..00n}` (hyphen in welder_id allowed; backend accepts).
- **Expert comparison:** Use expert-benchmark's latest session (`sess_expert-benchmark_005`) instead of `sess_expert_001`; or retain sess_expert_001 as dedicated baseline (issue says expert-benchmark latest).
- **Random seed:** Use `random.seed(42)` in seed script for reproducible volatile arc.

---

## 5. Approach Options

### Option A: Single mock_welders.py + extend mock_sessions
- **Description:** Add `backend/data/mock_welders.py` with WELDER_ARCHETYPES and `generate_score_arc` (for validation only). Add `generate_frames_for_arc(arc_type, session_index)` and `generate_session_for_welder(welder_id, session_index)` in mock_sessions.py. Seed route imports from both and loops archetypes.
- **Pros:** Single source of truth; clear separation; mock_sessions owns frame physics; easy to test.
- **Cons:** mock_sessions grows; cross-file dependency.
- **Key risk:** Frame tuning for 6 arc types may require iteration.
- **Complexity:** Medium

### Option B: Standalone mock_welders.py with embedded frame generator
- **Description:** `mock_welders.py` contains archetypes, `generate_frames_for_arc`, and `generate_session_for_welder` (building Session). mock_sessions.py unchanged; dev route imports only from mock_welders.
- **Pros:** mock_sessions untouched; all arc logic in one file.
- **Cons:** Duplicates `generate_frames` / thermal logic or imports heavily from mock_sessions.
- **Key risk:** Divergence from mock_sessions physics model.
- **Complexity:** Medium

### Option C: Config-driven with minimal code
- **Description:** Archetypes in JSON/TOML; Python reads config and drives existing `generate_frames` via parameterized closures. No new physics.
- **Pros:** Easy to add archetypes without code changes.
- **Cons:** Config doesn't capture closure logic; still need Python generators.
- **Key risk:** Over-abstracted for 10 fixed archetypes.
- **Complexity:** Low–Medium

### Option D: Reuse demo path, migrate Seagull to demo
- **Description:** Use existing `getDemoTeamData`/`DEMO_WELDERS` and add 10 welders; switch Seagull to fetch from backend instead of demo-config.
- **Pros:** Reuses demo infra.
- **Cons:** Demo path is browser-only, no frame/score fetch; Seagull already fetches; different data shapes.
- **Key risk:** Conflating two demo modes (browser vs API).
- **Complexity:** High (migration)

**Recommendation:** Option A. Keeps frame physics in mock_sessions; mock_welders holds archetypes and orchestration; clean handoff between files.

---

## 6. Prototype Results

### Prototype 1: Arc → Features → Score mapping
- **What was tested:** Whether arc-specific signal parameters (angle looseness, amps stability, thermal asymmetry) can produce target score ranges.
- **Code:** `backend/scripts/prototype_arc_scoring.py` — parameterized `arc_angle_tight`, `arc_angle_drift`, `arc_amps_stable`/`unstable`, `arc_volts_stable`/`unstable`; `make_session_for_arc(arc_type, session_idx)`; `extract_features` → `score_session`.
- **Result:** Prototype written; execution was not run in this environment. Based on codebase: expert has amps_stddev ~1.2, angle_max_deviation ~1, novice has amps ~12, angle ~21. Rule thresholds: amps≤5, angle≤5, thermal≤60, heat_diss≤40, volts≤1. Tuning angle_stddev 2°→8° and thermal asymmetry 10→40°C will shift scores predictably. Volatile will need `disable_sensor_continuity_checks=True`.
- **Decision:** Proceed. Implement `generate_frames_for_arc` with tunable params; run prototype locally during impl to validate ranges; accept ±5–10 point variance.

### Prototype 2: Session ID derivation
- **What was tested:** Frontend can derive session IDs from welder id + session count.
- **Code:** `const latestSessionId = \`sess_${welder.id}_${String(welder.sessionCount).padStart(3,'0')}\`;`
- **Result:** Trivial; no prototype needed. WELDERS config will include `{ id, name, sessionCount }`.
- **Decision:** Proceed.

### Prototype 3: Badge derivation
- **What was tested:** last 2 scores → improving / declining / neutral.
- **Code:** `const last = scores[scores.length-1]; const prev = scores[scores.length-2]; const badge = last > prev ? 'on_track' : last < prev ? 'needs_attention' : 'neutral';`
- **Result:** Matches `generateAIFeedback` trend logic; straightforward.
- **Decision:** Proceed.

---

## 7. Recommended Approach

**Chosen approach:** Option A — Single mock_welders.py + extend mock_sessions

**Justification (min 150 words):**

Option A keeps the physics model in mock_sessions (where `generate_frames`, `generate_thermal_snapshots`, and signal callables live) while introducing a thin orchestration layer in mock_welders.py. The extractor and scorer are unchanged; we only add parameterized signal generators that vary by arc_type and session_index. This fits existing patterns: expert_angle/novice_angle are already callables; we add arc_angle(arc_type, session_idx) that returns a closure for `generate_frames`. The seed route loops WELDER_ARCHETYPES, calls `generate_session_for_welder(welder_id, archetype, session_idx)` for each session, and persists. Wipe derives session IDs from the same archetypes—single source of truth. Frontend WELDERS gets `{ id, name, sessionCount }`; latestSessionId and secondLatestSessionId are derived. No new endpoints, no schema change. Risk is bounded: volatile/declining need `disable_sensor_continuity_checks=True` (as novice already does); we use `random.seed(42)` for reproducible demos. The main uncertainty is hitting exact score ranges; we accept ±5–10 variance and iterate during implementation.

**Trade-offs accepted:**
- Score ranges may be ±5–10 from archetype base/delta; we tune iteratively.
- 20 fetchScore calls on dashboard load; acceptable for demo; no batching in MVP.
- sess_expert_001 removed from seed (or kept only if we retain it for backward compat); we use expert-benchmark's latest for comparison.

**Fallback approach:** If frame tuning fails to hit ranges, fall back to Option B (standalone mock_welders with more aggressive parameter overrides) or relax acceptance criteria for score variance.

---

## 8. Architecture Decisions

| Decision | Options | Chosen | Reason | Reversibility | Impact |
|----------|---------|--------|--------|---------------|--------|
| Archetype storage | A: Python dict, B: JSON | A | Simpler; no file I/O; matches mock_sessions style | Easy | Locked in mock_welders.py |
| Frame generator location | A: mock_sessions, B: mock_welders | A (extend mock_sessions) | Physics lives in mock_sessions | Easy | Reuse generate_frames |
| Session ID convention | A: sess_{id}_{nnn}, B: sess_{id}_v{n} | A | Matches issue spec | Easy | Frontend derives from pad |
| Expert comparison baseline | A: sess_expert_001, B: expert-benchmark latest | B | Issue specifies expert-benchmark latest | Easy | Welder report fetches sess_expert-benchmark_005 |
| Badge data source | A: Fetch last 2 scores per welder, B: Backend batch | A | Zero new endpoints; Promise.allSettled | Easy | 20 fetchScore on load |
| Historical scores for welder report | A: Fetch all sess_xxx_001..00n, B: New list-by-operator | A | Zero new endpoints | Easy | Up to 5 fetchScore per welder |
| Random seed for volatile | A: seed(42), B: no seed | A | Reproducible demos | Easy | Deterministic volatile arc |
| Wipe scope | A: Derive from archetypes, B: Hardcode ~45 IDs | A | Single source of truth | Easy | Wipe matches seed |

---

## 9. Edge Cases

| Category | Scenario | Handling | Graceful? |
|----------|----------|----------|-----------|
| Empty/null | No sessions seeded | Dashboard cards show "Score unavailable"; no badge | Partial (no empty-state message) |
| Empty/null | Welder has 0 sessions | sessionCount=0; no latestSessionId; skip fetch; show "Score unavailable" | Partial |
| Empty/null | Welder has 1 session | Badge = neutral (need 2 for improving/declining) | Graceful |
| Max scale | 10 welders × 2 fetchScore = 20 concurrent | Promise.allSettled isolates failures | Graceful |
| Max scale | Welder report: 5 fetchScore + 2 fetchSession | Acceptable for 5 sessions | Graceful |
| Concurrent | User navigates away during fetch | useEffect cleanup; mounted check | Graceful |
| Concurrent | Rapid refresh of dashboard | Each load refetches; no dedup | Partial |
| Network | One fetchScore fails | Promise.allSettled; that card shows "Score unavailable" | Graceful |
| Network | All fetchScore fail | All cards show "Score unavailable"; no badges | Graceful |
| Network | fetchSession 404 for welder | Error state; "Session not found" | Graceful |
| Browser | Slow network, 20 requests | May timeout; consider future batching | Partial |
| Browser | Invalid welder id in URL | 404 or error; link from dashboard uses valid ids | Graceful |
| Permission | Seed/wipe in production | 403 when not ENV=development | Graceful |
| Session | Welder id typo (e.g. mike_chen vs mike-chen) | 404; IDs must match archetype | Partial |
| Data | Volatile arc non-deterministic without seed | random.seed(42) in seed script | Graceful |
| Data | Declining arc violates continuity | disable_sensor_continuity_checks=True | Graceful |
| Data | expert-benchmark not seeded | Welder report comparison fetch 404 | Partial (error state) |

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|--------|---------------|------------|
| Frame params don't hit target score ranges | Med | Med | Scores outside ±10 of target in prototype | Iterative tuning; accept ±5–10; document expected ranges |
| Volatile arc non-reproducible | Med | Low | Different scores across seed runs | random.seed(42) before generation |
| Continuity violations on declining/volatile | Med | Low | Session validation fails on ingest | Set disable_sensor_continuity_checks=True |
| Wipe misses sessions if ID drift | Low | Med | Orphan mock sessions after wipe | Derive IDs from WELDER_ARCHETYPES; single source |
| seed_demo_data.py diverges from API seed | Low | Low | CLI seed produces different data than API | Update script to call shared generator or mirror logic |
| Dashboard 20 fetchScore timeout | Low | Med | Slow load on poor network | Promise.allSettled; consider batch endpoint later |
| Expert comparison 404 if expert-benchmark not seeded | Low | Med | Welder report breaks for all welders | Seed before demo; document dependency |
| Badge logic wrong for volatile (swings) | Low | Low | Volatile shows wrong badge | Use last 2 scores; volatile may show improving/declining/stable correctly |
| LineChart receives wrong shape for historical | Low | Low | Chart breaks | LineChart expects {date, value}[]; map scores to "Session 1", etc. |
| mock_sessions circular import | Low | Low | ImportError at startup | mock_welders imports mock_sessions; no reverse import |
| **CRITICAL** Rule thresholds change in future | Low | High | All arc scores shift | Don't change thresholds for mock; document coupling |
| Typo `bae` in spec | N/A | N/A | — | Use `base` in implementation |

---

## 11. Exploration Summary

**Files to create:**
- `backend/data/mock_welders.py` — WELDER_ARCHETYPES, generate_score_arc (validation), generate_session_for_welder (or similar) calling mock_sessions

**Files to modify:**
- `backend/data/mock_sessions.py` — Add generate_frames_for_arc(arc_type, session_index) + arc-specific signal builders
- `backend/routes/dev.py` — Extend seed to loop archetypes, generate ~45 sessions; extend wipe to delete all derived session IDs
- `backend/scripts/seed_demo_data.py` — Call shared generator or extend to seed all 10 archetypes
- `my-app/src/app/seagull/page.tsx` — WELDERS = 10 entries with id, name, sessionCount; derive latestSessionId, secondLatestSessionId; fetch both for badge; add badge UI
- `my-app/src/app/seagull/welder/[id]/page.tsx` — WELDER_MAP from 10 welders; expert comparison = sess_expert-benchmark_005; replace MOCK_HISTORICAL with fetched scores for sess_{id}_001..00n
- `backend/tests/test_dev_routes.py` — Update expected session count; add test for wipe of ~45 sessions
- `backend/tests/test_mock_sessions.py` or new `test_mock_welders.py` — Tests for generate_score_arc, generate_frames_for_arc score ranges

**New dependencies:** none

**Bundle impact:** ~0 KB (no new frontend deps)

**Critical path order:**
1. mock_welders.py (archetypes + orchestration)
2. mock_sessions.py (generate_frames_for_arc)
3. dev.py seed/wipe
4. seed_demo_data.py
5. seagull/page.tsx (dashboard + badge)
6. seagull/welder/[id]/page.tsx (historical scores, expert comparison)
7. Tests

**Effort estimate:** Backend 10h + Frontend 3h + Testing 2h + Review 1h = Total 16h, confidence 75%

**Blockers for planning:**
- None. Open question: retain sess_expert_001 for backward compatibility (e.g. external links) or remove and use only expert-benchmark? Assume remove unless product specifies retention.
