# Threshold Configuration Admin UI

## 1. Title

`[Feature] Configurable weld quality thresholds per process type (MIG/TIG/Stick/Flux Core)`

---

## 2. TL;DR

Today, scoring and micro-feedback use hardcoded thresholds (45°, ±5°, ±15°, 20°C thermal) across the entire codebase. Procurement teams evaluating the system need to calibrate to their spec sheet — "we calibrate to your spec" is a sales differentiator. This feature adds a `weld_thresholds` table, admin UI at `/admin/thresholds`, and wires thresholds into backend scoring and frontend micro-feedback. Supervisors see which spec was used on each report. Effort: ~16–24h across backend (DB + API + scoring), frontend (admin page + WelderReport callout), and tests.

---

## 3. Root Cause Analysis

**Level 1:** Scores don't match customer spec sheets.  
**Level 2:** Thresholds are hardcoded in multiple places (rule_based.py, extractor.py, micro-feedback.ts).  
**Level 3:** No configuration surface exists — thresholds were designed as tuning constants, not product configuration.  
**Level 4:** MVP scope did not include "calibrate to customer spec" as a requirement.  
**Level 5:** Root cause: thresholds were built as developer knobs, not as a configurable product feature for procurement evaluation.

---

## 4. Current State

**What exists today:**

| File / Component | Description |
|------------------|-------------|
| `backend/scoring/rule_based.py` | 5 rules; hardcoded `ANGLE_CONSISTENCY_THRESHOLD=5`, `THERMAL_SYMMETRY_THRESHOLD=60`, `AMPS_STABILITY_THRESHOLD=5`, `VOLTS_STABILITY_THRESHOLD=1`, `HEAT_DISS_CONSISTENCY_THRESHOLD=40` |
| `backend/features/extractor.py` | Line 55: `max(abs(a - 45) for a in angles)` — angle target 45° baked in |
| `my-app/src/lib/micro-feedback.ts` | `ANGLE_TARGET_DEG=45`, `ANGLE_WARNING_THRESHOLD_DEG=5`, `ANGLE_CRITICAL_THRESHOLD_DEG=15`, `THERMAL_VARIANCE_THRESHOLD_CELSIUS=20` |
| `backend/routes/sessions.py` | `GET /api/sessions/{session_id}/score` — calls `score_session()` with no weld-type context |
| `backend/services/thermal_service.py` | Heat dissipation only; no threshold constants |
| `backend/database/models.py` | `SessionModel` with `weld_type` (String) — currently holds metal identifiers like `"mild_steel"` |
| `backend/models/session.py` | `Session.weld_type` — same semantic |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | WelderReport: shows `{score}/100`, AI summary; no threshold callout |
| `my-app/src/app/demo/team/[welderId]/page.tsx` | Same pattern for demo path |
| `my-app/src/components/welding/ScorePanel.tsx` | Displays `total`, `rules` with `actual_value / threshold` |
| `my-app/src/lib/api.ts` | `fetchScore(sessionId)`, `fetchSession()`; no thresholds API |
| `backend/alembic/versions/*.py` | Migrations 001–003; no `weld_thresholds` table |
| `/admin/*` | Does not exist — no admin routes or layout |

**What's broken or missing:**

1. **Admin cannot configure thresholds** — User wants to set MIG vs TIG vs Stick vs Flux Core specs. Today: impossible. Workaround: none; sales cannot demo "calibrate to your spec."
2. **Scoring ignores process type** — User expects MIG 45° vs TIG 75° to be scored differently. Today: all sessions use the same 45° target and 5° pass/fail. Workaround: none.
3. **Micro-feedback uses fixed constants** — User expects warning/critical zones to match configured thresholds. Today: micro-feedback hardcodes 45°, ±5°, ±15°, 20°C. Workaround: none.
4. **Report hides which spec was used** — User (supervisor) wants to see "Evaluated against MIG spec — Target 45° ±5°". Today: no callout. Workaround: none.

---

## 5. Desired Outcome

**User flow after fix:**

1. **Admin configures thresholds:** Admin navigates to `/admin/thresholds`, selects MIG tab, edits Target angle 45°, Warning ±5°, Critical ±15°, thermal warning/critical °C, amps/volts stability. Saves → `PUT /api/thresholds/mig`. System persists to DB.
2. **Scoring uses thresholds:** Session has process type (e.g. `mig`). `get_session_score` loads thresholds for that process type, passes to `extract_features` (angle target) and `score_session` (all thresholds). Score reflects configured spec.
3. **Micro-feedback uses thresholds:** When generating micro-feedback, client receives thresholds (from session metadata or a separate fetch) and passes them to `generateMicroFeedback(frames, thresholds)`.
4. **Report shows spec:** Below the score, WelderReport displays: "Evaluated against MIG spec — Target 45° ±5°".

**Edge flows:**

- **Error state:** Admin saves invalid values (e.g. critical < warning) → backend validates, returns 422 with field errors; form shows inline validation.
- **Empty state:** First load before any thresholds exist → seeded defaults from migration; admin sees pre-filled forms.

**Acceptance criteria:**

1. User can open `/admin/thresholds` and see tabs: MIG | TIG | Stick | Flux Core.
2. User can edit angle target, warning margin, critical margin per process type and save; changes persist via `PUT /api/thresholds/:weld_type`.
3. User sees a small inline arc/SVG diagram next to angle inputs showing the target angle.
4. User receives inline validation errors when warning > critical or values out of range.
5. System returns all thresholds via `GET /api/thresholds` with weld_type as key.
6. System scores sessions using thresholds from `weld_thresholds` for the session's process type (not hardcoded constants).
7. System computes `angle_max_deviation` using the configured target from thresholds (not hardcoded 45°).
8. Micro-feedback uses configured angle and thermal thresholds when available.
9. WelderReport (Seagull and demo) displays a callout: "Evaluated against {process} spec — Target {target}° ±{warning}°".
10. Session score API response includes or allows derivation of active threshold spec for display.
11. Thresholds are cached in backend (in-memory or similar) — no DB hit per score request.
12. Automated tests verify: GET/PUT thresholds, scoring with different thresholds, WelderReport callout when spec present.

**Out of scope:**

1. **Per-operator thresholds** — Only process-type level; no operator-specific overrides. Reason: MVP scope.
2. **Threshold versioning/audit history** — No history of who changed what when. Reason: deferred to post-MVP.
3. **Threshold import/export** — No CSV/JSON bulk import. Reason: manual form entry sufficient for demo.

---

## 6. Constraints

- **Tech stack:** Backend Python + FastAPI + PostgreSQL + SQLAlchemy; frontend React + Next.js + Tailwind.
- **Performance:** Threshold fetch cached; no N+1 per score. Target: score latency unchanged.
- **Browser:** Same as MVP (Chrome, Firefox, Safari recent).
- **Accessibility:** WCAG 2.1 AA for admin form (labels, focus, errors).
- **Blocked by:** None.
- **Blocks:** "Calibrate to spec" sales narrative; procurement evaluation workflows.

---

## 7. Risks

| Risk | Probability | Impact | Mitigation |
|------|--------------|--------|------------|
| Session.weld_type semantic collision — currently "mild_steel" (metal), thresholds need "mig" (process) | High | High | Add `process_type` to session or introduce mapping; resolve in Open Questions. |
| Extractor and rule_based need threshold injection — current API is session-only | Med | Med | Refactor `extract_features(session, thresholds?)` and `score_session(session, features, thresholds)`; add optional params, fallback to defaults. |
| Micro-feedback is client-side; thresholds must be passed in or fetched | Med | Low | Extend `generateMicroFeedback` to accept optional thresholds; fetch via API from session metadata or GET thresholds. |
| Admin route auth — /admin currently unprotected | Med | Med | Add basic auth or defer to infra; document in constraints. |
| Cache invalidation on threshold update — stale scores if cache not cleared | Low | Med | On PUT, invalidate cache; use short TTL or event-based invalidation. |
| Breaking existing tests that assume hardcoded 45° | Med | Low | Update fixtures to pass thresholds or use defaults; ensure backward compatibility. |

---

## 8. Open Questions

| Question | Current assumption | Confidence | Resolver |
|----------|--------------------|------------|----------|
| How does session specify process type (mig/tig/stick/flux_core)? `weld_type` today is metal (mild_steel). | Add `process_type` column to sessions; default "mig" for backfill. | Low | Product / Eng |
| TIG table in task spec shows "75°10°" — typo? Intended "75° ±10°"? | Assume 75° target, ±10° warning. | Low | Task author |
| Should GET /api/sessions/{id}/score include `active_threshold_spec` in response? | Yes — include `{ process_type, angle_target, angle_warning }` for display. | Med | Eng |
| Admin auth: implement now or stub? | Stub/placeholder; document that production will add auth. | Med | Eng |

---

## 9. Classification

- **Type:** feature
- **Priority:** P2 (standard)
- **Effort:** M (16–24h)
- **Effort breakdown:** Frontend 8h + Backend 8h + Testing 4h + Review 2h = Total 22h
