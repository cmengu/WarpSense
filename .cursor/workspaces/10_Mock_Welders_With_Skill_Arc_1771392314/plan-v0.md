
Summary of the implementation plan:

---

## Plan Summary

Implementation plan is in **`.cursor/taskspace/20260218_130707/plan-10-mock-welders.md`**.

### Phase Breakdown (5 phases, 17 steps, ~16h)

| Phase | Goal | Est. |
|-------|------|------|
| **Phase 1** — Backend mock data layer | 10 archetypes, `generate_score_arc`, `generate_frames_for_arc`, `generate_session_for_welder` | 5h |
| **Phase 2** — Seed & wipe | ~45 sessions seeded, wipe removes all, seed_demo_data aligned | 3h |
| **Phase 3** — Dashboard | 10 welder cards, coaching badges (On track / Needs attention) | 3h |
| **Phase 4** — Welder report | Historical scores from fetch, `sess_expert-benchmark_005` as expert baseline | 2h |
| **Phase 5** — Tests | `test_mock_welders.py`, updates to `test_dev_routes.py` | 3h |

### Main implementation details

1. **`mock_welders.py`** — `WELDER_ARCHETYPES` (10 entries) and `generate_score_arc` for validation only (correct `base` vs spec typo).
2. **`mock_sessions.py`** — `generate_frames_for_arc(arc_type, session_index)` and `generate_session_for_welder(welder_id, arc_type, session_index, session_id)`; volatile/declining use `disable_sensor_continuity_checks=True`.
3. **Seed/wipe** — IDs derived from archetypes (single source of truth), `random.seed(42)` before generation.
4. **Dashboard** — `WELDERS` with `sessionCount`; `latestSessionId`/`secondLatestSessionId`; badge from last vs second-last score.
5. **Welder report** — `MOCK_HISTORICAL` replaced with fetched scores; expert comparison uses `sess_expert-benchmark_005`.

### Risk mitigations

- Frame tuning: accept ±5–10 variance; tune angle/amps/volts.
- Volatile reproducibility: `random.seed(42)` in seed route.
- Continuity failures: `disable_sensor_continuity_checks=True` for volatile and declining.
- Wipe coverage: IDs derived from `WELDER_ARCHETYPES`.

The plan includes per-step verification, CRITICAL steps with full code, and a pre-flight checklist and risk heatmap.
