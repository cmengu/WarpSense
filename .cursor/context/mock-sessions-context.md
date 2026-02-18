# Mock Sessions — Context

> **For AI:** Use when working on seed data, WELDER_ARCHETYPES, dev routes, or Seagull dashboard. Do not reimplement; extend existing patterns.

---

## What Exists

**10 mock welders** with skill arcs (fast_learner, declining, volatile, consistent_expert, plateaued, new_hire). Each archetype drives frame generation via arc_type; sessions are `sess_{welder_id}_{001..00n}`.

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/data/mock_welders.py` | WELDER_ARCHETYPES — welder_id, name, arc, sessions, base, delta |
| `backend/data/mock_sessions.py` | generate_session_for_welder, generate_frames_for_arc, expert/novice signals |
| `backend/scripts/seed_demo_data.py` | Idempotent seed; run from deploy or manually |
| `backend/routes/dev.py` | POST /api/dev/seed-mock-sessions, POST /api/dev/wipe-mock-sessions (ENV=development or DEBUG=1) |

---

## Data Flow

```
WELDER_ARCHETYPES → generate_session_for_welder(welder_id, arc, session_idx, sid)
  → generate_frames_for_arc(arc, session_idx)
  → generate_frames() with arc-specific get_amps/get_volts/get_angle
  → SessionModel.from_pydantic(session) → db.add
```

---

## Arc Types

| arc | Behavior |
|-----|----------|
| fast_learner | Angle tightens over sessions (looseness 4°→1°) |
| declining | Angle drift grows with session |
| volatile | Unstable amps/volts, oscillating angle |
| consistent_expert | Stable expert signals |
| plateaued, new_hire | Modest variation |

---

## Constraints

- **Idempotent seed:** Skips when existing count == expected; spot-checks operator_id before skip.
- **Dev-only routes:** 403 when not ENV=development or DEBUG=1.
- **Session IDs:** `sess_{welder_id}_{001..00n}` — must match WELDER_ARCHETYPES.
- **Seagull page:** Expects welder_ids from mock_welders; `getLatestSessionId` uses session count.

---

## Integration

- **Seagull dashboard:** `/seagull` — cards from WELDER_ARCHETYPES; links to `/seagull/welder/[id]`.
- **Welder report:** Fetches latest session `sess_{welderId}_{n:03d}`; expects seed to have run.
- **Frontend constants:** `WELDER_SESSION_COUNT`, `WELDER_DISPLAY_NAMES` in `seagull/welder/[id]/page.tsx` — must stay in sync with mock_welders.py.

---

## Adding a New Welder

1. Add entry to WELDER_ARCHETYPES in `mock_welders.py`.
2. Add `welder_id` → session count and display name in `seagull/welder/[id]/page.tsx`.
3. Run seed: `POST /api/dev/seed-mock-sessions` or `python backend/scripts/seed_demo_data.py`.
