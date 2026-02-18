# 10 Mock Welders With Skill Arcs

**Type:** Feature  
**Priority:** P2  
**Effort:** M (8–16h)  
**Status:** Open  

---

## 1. Title

`[Feature] 10 mock welders with skill arcs for enterprise sales demo`

---

## 2. TL;DR

The Seagull dashboard currently shows 2 welders (Mike Chen, Expert Benchmark) with single-session scores. For an enterprise sales demo, a supervisor needs to see 10 welders with distinct skill arcs—fast learners, declining, plateaued, volatile, new hires—so the story "3 improving, 2 declining, 1 star" lands credibly. Today there is no backend data for this: mock sessions are hardcoded expert/novice only, no arc-driven frame generation, and no coaching-status logic on the dashboard. The fix: add `mock_welders.py` with 10 archetypes, an arc-aware frame generator that produces rule-consistent frame data (not just faked scores), extend the seed route to create ~45 sessions with correct timestamps and `operator_id`=welder_id, and update the Seagull dashboard to show all 10 with green/amber coaching badges derived from last-2-scores. Effort: ~150 lines backend Python, ~30 lines frontend, zero new API endpoints.

---

## 3. Root Cause Analysis

1. **Surface:** Dashboard shows only 2 welders; no variety for demos.
2. **Why:** `WELDERS` in `seagull/page.tsx` is hardcoded to Mike Chen and Expert Benchmark; seed creates only 2 sessions.
3. **Why that:** Original Seagull pilot was minimal (2 welders); no requirement for demo variety.
4. **Why that:** MVP focused on replay/score/heatmap; sales-demo use case was not in scope.
5. **Root cause:** No mock data layer for welder archetypes; no arc-driven frame generation that aligns frame features (angle, thermal, amps) with the scoring rules, so even if we faked 10 scores, drill-down to welder report would show inconsistent heatmaps/micro-feedback.

---

## 4. Current State

**What exists today:**

| File / Component | Description |
|-----------------|-------------|
| `backend/data/mock_sessions.py` | `generate_expert_session`, `generate_novice_session`, `generate_frames` with `get_amps`, `get_volts`, `get_angle` callables. Expert: stable 150A, 45°; novice: erratic amps, angle drift 45°→65°. No arc-type parameter. |
| `backend/routes/dev.py` | `POST /api/dev/seed-mock-sessions` seeds `sess_expert_001`, `sess_novice_001`; `POST /api/dev/wipe-mock-sessions` deletes same 2 IDs. |
| `backend/scripts/seed_demo_data.py` | Idempotent CLI seed for `sess_expert_001`, `sess_novice_001`; used by deploy. |
| `backend/database/models.py` | `SessionModel` has `operator_id` (indexed); `FrameModel` via `frame_data` JSON. |
| `backend/models/session.py` | `Session` Pydantic model: `operator_id`, `session_id`, `frames`, etc. |
| `backend/features/extractor.py` | `extract_features()` → `amps_stddev`, `angle_max_deviation`, `north_south_delta_avg`, `heat_diss_stddev`, `volts_range`. |
| `backend/scoring/rule_based.py` | `score_session(session, features)` → 0–100 (5 rules × 20). |
| `my-app/src/app/seagull/page.tsx` | Dashboard: `WELDERS` = 2 entries; fetches `fetchScore(sessionId)` per welder; displays name, score, link. No coaching badge. |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | `WELDER_MAP` = 2 entries; `MOCK_HISTORICAL` = `[68,72,75]` hardcoded; fetches latest session + expert session + score; uses `generateAIFeedback(session, score, MOCK_HISTORICAL)`. |
| `my-app/src/lib/api.ts` | `fetchScore(sessionId)` → `SessionScore`; no batch/list endpoint. |
| `GET /api/sessions` | Returns 501 Not Implemented; no way to list sessions by operator. |

**What's broken or missing:**

| Gap | User wants | Current behavior | Why |
|-----|------------|------------------|-----|
| Demo variety | See 10 welders with distinct arcs (improving, declining, plateaued, etc.) | Only 2 welders; no arc differentiation | No archetype data; seed creates 2 sessions only |
| Coaching visibility | At-a-glance "Needs attention" vs "On track" per welder | No badge | No logic for last-2-scores trend |
| Drill-down consistency | Click welder → heatmap/micro-feedback matches arc (e.g. declining shows angle drift) | N/A (only 2) | Frame generation is expert/novice only; no arc-specific angle/thermal/amps profiles |
| Score history per welder | Real trend in welder report | `MOCK_HISTORICAL` hardcoded `[68,72,75]` | No multi-session fetch; no session IDs per welder |
| Wipe completeness | Reset all mock data | Wipe only deletes 2 session IDs | New ~45 sessions would remain after wipe |

**Workarounds:** None. Demo is limited to 2 welders.

---

## 5. Desired Outcome

**User flow after fix:**

1. **Primary flow:** Supervisor opens `/seagull`. Sees 10 welder cards in a grid. Each card shows name, latest score (e.g. 72/100), and a badge: green "On track" (improving), neutral (stable/plateaued), or amber "Needs attention" (declining). Clicks a card → `/seagull/welder/{id}` with real session data, heatmap, AI feedback, and trend chart derived from actual score history.
2. **Edge—error state:** One welder's score fetch fails → that card shows "Score unavailable" and no badge; other 9 cards render normally (Promise.allSettled).
3. **Edge—empty state:** No sessions seeded → all cards show "Score unavailable"; badges not shown.

**Acceptance criteria:**

1. User can open `/seagull` and see exactly 10 welder cards (Mike Chen, Sara Okafor, James Park, Lucia Reyes, Tom Bradley, Ana Silva, Derek Kwon, Priya Nair, Marcus Bell, Expert Benchmark).
2. User can see each welder's latest score (0–100) computed by the backend from frame data.
3. User can see green "On track" badge on welders whose last 2 scores are improving (e.g. fast_learner, new_hire archetypes).
4. User can see amber "Needs attention" badge on welders whose last 2 scores are declining (e.g. declining archetypes).
5. User can see neutral or no badge on welders who are stable/plateaued/volatile or have fewer than 2 sessions.
6. System stores `operator_id` = welder_id (e.g. `mike-chen`) on each seeded session for traceability.
7. User can click a welder card and land on `/seagull/welder/{id}` with heatmap and micro-feedback that reflect that welder's arc (e.g. declining welder shows angle drift in thermal asymmetry).
8. User can see a welder report trend chart driven by real fetched scores, not hardcoded `MOCK_HISTORICAL`.
9. `POST /api/dev/seed-mock-sessions` seeds ~45 sessions (3–5 per welder) with session IDs following `sess_{welder_id}_{001..00n}`.
10. `POST /api/dev/wipe-mock-sessions` deletes all mock sessions seeded by the extended seed (including the new ~45).
11. All seeded sessions pass existing validation (frame continuity, thermal distance, etc.).
12. Backend unit test verifies `generate_score_arc` and `generate_frames_for_arc` produce expected score ranges and feature magnitudes for each arc type.

**Out of scope:**

1. **New API endpoint for listing sessions by operator** — Task specifies zero new endpoints; frontend derives session IDs from a shared convention.
2. **ML or auto-tuned scoring** — Scoring stays rule-based; mock data is tuned to produce target score arcs.
3. **Real-time or streaming updates** — Dashboard loads once; no WebSocket or polling.

---

## 6. Constraints

- **Tech stack:** Backend Python/FastAPI; frontend React/Next.js/TypeScript. Must use existing `SessionModel`, `extract_features`, `score_session`; no new DB columns.
- **Performance:** Dashboard fetches up to 20 `fetchScore` calls (2 per welder for badge); acceptable with `Promise.allSettled`. No streaming required.
- **Data integrity:** Append-only raw data; scoring deterministic. Frame data must drive scores—no faked scores stored; scores computed from frames.
- **Blocked by:** None.
- **Blocks:** Investor demo; Seagull pilot expansion.

---

## 7. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-------------|
| Rule-based scores don't hit target ranges (e.g. base 58 + delta 4) exactly | Med | Low | Tune `generate_frames_for_arc` params iteratively; accept ±5 point variance; scoring is deterministic from features |
| Volatile arc's `random.choice` makes seeded data non-deterministic | Med | Low | Use seeded RNG in seed script (`random.seed(42)`) for reproducible demos |
| `disable_sensor_continuity_checks` required for volatile/declining arcs due to large amps/angle swings | Med | Low | Set flag per session when arc produces continuity violations; existing novice session already uses this |
| 20 concurrent `fetchScore` calls cause timeout under slow network | Low | Med | `Promise.allSettled` isolates failures; consider batching if needed (out of scope for MVP) |
| Wipe misses sessions if ID convention drifts | Low | Med | Derive mock session ID list from `WELDER_ARCHETYPES`; single source of truth |
| Welder report expert comparison breaks if `sess_expert_001` removed | Low | Med | Retain `sess_expert_001` or designate `expert-benchmark` latest as comparison baseline; document in implementation |
| `seed_demo_data.py` diverges from seed route | Low | Low | Update script to call shared generator or mirror seed route logic |

---

## 8. Open Questions

| Question | Assumption | Confidence | Resolver |
|----------|------------|------------|----------|
| Use `operator_id` for welder_id (no new `welder_id` column)? | Yes; `operator_id` holds welder slug (mike-chen, etc.) | High | Tech lead |
| Keep `sess_expert_001` for welder report comparison, or use expert-benchmark's latest? | Use expert-benchmark's latest session (`sess_expert-benchmark_005`) as comparison baseline | Med | Product |
| Fix typo in spec: `bae` → `base` in score formula? | Yes; implementation uses `base` | High | Dev |
| `generate_score_arc` used only for validation/tuning, not for storing scores? | Correct; actual scores come from `score_session(extract_features(session))` | High | Dev |
| 🔴 Session ID format: `sess_mike-chen_001` or `sess_mike_chen_001` (hyphen vs underscore)? | Hyphen allowed in session_id; use `sess_{welder_id}_{nnn}` | Med | Backend team |

---

## 9. Classification

- **Type:** feature
- **Priority:** P2 (standard)
- **Effort:** M (8–16h)
- **Effort breakdown:** Backend 10h (mock_welders + frame generator + seed) + Frontend 3h (dashboard + welder report) + Testing 2h + Review 1h = **16h**

---

## Appendix: Archetype + Generator Reference (from task)

```python
WELDER_ARCHETYPES = [
  {"welder_id": "mike-chen",       "name": "Mike Chen",        "arc": "fast_learner",      "sessions": 5, "base": 58, "delta": +4},
  {"welder_id": "sara-okafor",     "name": "Sara Okafor",      "arc": "consistent_expert", "sessions": 5, "base": 88, "delta": +1},
  {"welder_id": "james-park",      "name": "James Park",       "arc": "plateaued",         "sessions": 5, "base": 71, "delta": 0},
  {"welder_id": "lucia-reyes",     "name": "Lucia Reyes",      "arc": "declining",         "sessions": 5, "base": 76, "delta": -4},
  {"welder_id": "tom-bradley",     "name": "Tom Bradley",      "arc": "new_hire",          "sessions": 3, "base": 42, "delta": +6},
  {"welder_id": "ana-silva",       "name": "Ana Silva",        "arc": "volatile",           "sessions": 5, "base": 65, "delta": 0},
  {"welder_id": "derek-kwon",      "name": "Derek Kwon",       "arc": "fast_learner",      "sessions": 5, "base": 61, "delta": +5},
  {"welder_id": "priya-nair",      "name": "Priya Nair",       "arc": "consistent_expert", "sessions": 5, "base": 91, "delta": 0},
  {"welder_id": "marcus-bell",     "name": "Marcus Bell",      "arc": "declining",         "sessions": 5, "base": 80, "delta": -5},
  {"welder_id": "expert-benchmark","name": "Expert Benchmark", "arc": "consistent_expert", "sessions": 5, "base": 93, "delta": +0.5},
]

def generate_score_arc(base, delta, sessions, arc_type):
    # Note: fix typo "bae" → "base"
    # volatile: score = base + random.choice([-12, -6, 0, 8, 14])
    # else: score = base + (delta * i) + noise
```

**Frame generator targets per arc:**
- `angle_degrees` stddev: tight=2°, loose=8°, drifting=2°→8° over sessions (declining)
- `thermal N/S delta`: symmetric=<10°C, asymmetric=20–40°C (volatile)
- `amps` stability: stable=±2A, unstable=±8A (volatile)
