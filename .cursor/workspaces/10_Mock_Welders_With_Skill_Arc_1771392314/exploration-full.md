
Technical exploration for **10 Mock Welders With Skill Arcs** is documented in `.cursor/explore/10-mock-welders-exploration.md`. Summary:

---

## Findings

1. **Complexity:** Moderate — builds on existing mock sessions, seed/wipe, dashboard, and welder report.
2. **Risk:** Low across data loss, service disruption, security, dependencies, and rollback.
3. **Architecture:** Option A — `mock_welders.py` + extend `mock_sessions.py` with `generate_frames_for_arc()`.
4. **No new APIs** — Frontend derives session IDs as `sess_{welder_id}_{001..00n}` from `WELDER_ARCHETYPES` and uses `fetchScore` for scores and badges.
5. **Expert comparison:** Use expert-benchmark’s latest session (`sess_expert-benchmark_005`) instead of `sess_expert_001`.
6. **Arc tuning:** Frame generation must produce scores near target ranges; ±5–10 variance is acceptable. Volatile and declining arcs require `disable_sensor_continuity_checks=True`; use `random.seed(42)` for reproducibility.

---

## Prototype

A prototype script `backend/scripts/prototype_arc_scoring.py` is in place. Run it during implementation to validate feature → score ranges:

```bash
cd /Users/ngchenmeng/test && PYTHONPATH=backend python backend/scripts/prototype_arc_scoring.py
```

---

## Planning Handoff (Section 11)

| Item | Value |
|------|-------|
| **Files to create** | `backend/data/mock_welders.py` |
| **Files to modify** | `mock_sessions.py`, `dev.py`, `seed_demo_data.py`, `seagull/page.tsx`, `welder/[id]/page.tsx`, tests |
| **Dependencies** | None |
| **Bundle impact** | ~0 KB |
| **Critical path** | mock_welders → mock_sessions → dev seed/wipe → seed script → dashboard → welder report → tests |
| **Effort** | 16h (Backend 10h + Frontend 3h + Testing 2h + Review 1h), 75% confidence |
| **Blockers** | None. Open question: keep `sess_expert_001` for backward compatibility or remove? |
