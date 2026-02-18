
Here’s what was added and captured in the issue:

**Created:** `.cursor/issues/threshold-configuration-admin-ui.md`

**Highlights:**

1. **Root cause** — Thresholds are implemented as developer constants instead of configurable product settings.

2. **Current state** — Documented where thresholds are used:
   - `backend/scoring/rule_based.py` — 5 scoring rules
   - `backend/features/extractor.py` — 45° angle target (line 55)
   - `my-app/src/lib/micro-feedback.ts` — angle (45°, ±5°, ±15°) and thermal (20°C)
   - `backend/services/thermal_service.py` — only heat dissipation, no threshold constants (task spec corrected here)

3. **Semantic collision** — `session.weld_type` currently means metal (e.g. `"mild_steel"`), while the new thresholds expect process types (`mig`, `tig`, etc.). This is listed as an open question and a risk.

4. **Acceptance criteria** — Twelve criteria covering admin UI, API, scoring wiring, micro-feedback, WelderReport callout, and tests.

5. **Open questions** — Including the TIG spec typo (“75°10°” vs “75° ±10°”), how sessions specify process type, and score API response shape.

6. **Effort** — 22h total (8h frontend, 8h backend, 4h testing, 2h review).
