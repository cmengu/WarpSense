# Threshold Configuration — Context

> **For AI:** Use when working on weld quality thresholds, admin UI, or scoring rule parameters. Do not reimplement; extend existing patterns.

---

## What Exists

**Threshold admin UI** — CRUD for mig/tig/stick/flux_core. Backend: GET/PUT /api/thresholds; cached in-memory; invalidated on PUT. Frontend: /admin/thresholds with AngleArcDiagram, validation (warning ≤ critical).

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/routes/thresholds.py` | GET /api/thresholds, PUT /api/thresholds/:weld_type |
| `backend/services/threshold_service.py` | get_thresholds, get_all_thresholds, invalidate_cache; module-level cache |
| `backend/models/thresholds.py` | WeldTypeThresholds, WeldThresholdUpdate (Pydantic) |
| `backend/alembic/versions/004_weld_thresholds_and_process_type.py` | weld_thresholds table, seed mig default |
| `my-app/src/app/admin/thresholds/page.tsx` | Tabs (mig/tig/stick/flux_core), form, handleSave |
| `my-app/src/components/admin/AngleArcDiagram.tsx` | SVG semicircle showing target angle; aria-label for a11y |
| `my-app/src/types/thresholds.ts` | WeldTypeThresholds, ActiveThresholdSpec |
| `my-app/src/lib/api.ts` | fetchThresholds(), updateThreshold(weldType, body) |

---

## Data Model

**WeldTypeThresholds:**
- weld_type, angle_target_degrees, angle_warning_margin, angle_critical_margin
- thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius
- amps_stability_warning, volts_stability_warning, heat_diss_consistency

**Validation:** angle_target > 0; warning_margin ≤ critical_margin; thermal_warning ≤ thermal_critical.

---

## Backend Cache

- **In-memory:** weld_type → WeldTypeThresholds; loaded on first request.
- **Invalidation:** invalidate_cache() on PUT; _cache_loaded = False.
- **Limitation:** Process-local; multi-worker (Gunicorn) serves stale until restart. Document for MVP.

---

## Admin UI Flow

1. fetchThresholds() on mount → populate tabs.
2. User edits form (angle target, warning/critical margins, thermal, amps, volts, heat_diss).
3. handleSave: validate (isCompleteForm, warning ≤ critical), updateThreshold(active, form), refetch.

---

## AngleArcDiagram

- **Props:** angleTargetDegrees (number).
- **Accessibility:** role="img", aria-label="Target angle: {n} degrees".

---

## Constraints

- **Known process types:** mig, tig, stick, flux_core only; 422 for unknown.
- **No optional fields in PUT body:** All threshold fields required in WeldThresholdUpdate.
- **Frontend sync:** WELDER_ARCHETYPES / scoring use process_type; threshold row must exist for each.

---

## Integration

- **Scoring:** rule_based.py calls get_thresholds(db, process_type) from session weld_type.
- **Score response:** active_threshold_spec (angle_target, angle_warning, etc.) for frontend display on welder report.
