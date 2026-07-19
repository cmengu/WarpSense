# docs/ — project documentation

| Directory | Contents |
|---|---|
| `issues/` | Feature/bug write-ups from the `/create-issue` workflow. Several are cited by `@see` comments in source — update those references if you move or rename one. |
| `errors/` | Postmortems of recurring development/runtime errors (WebGL context loss, mock-data seeding). `errors/WEBGL_CONTEXT_LOSS.md` is cited by an ESLint rule and source comments — same rule. |
| `ops/` | Deployment and operations guides. |
| `business/` | Non-engineering strategy documents. |
| `archive/` | Point-in-time snapshots, completed or superseded plans, and docs describing code that no longer exists. Kept for the record; do not treat as current. |

Living engineering docs stay next to what they document, not here:
- Repo root: `README.md` (entry point), `STARTME.md` + `QUICK_START.md` (getting started), `LEARNING_LOG.md` (dev lessons; referenced by tooling and source comments).
- World-model suite at root: `STEPS.md` (single source of truth), `FUTURE_PLANS_WORLD_MODELS.md`, `WORLD_MODEL_IMPLEMENTATION_REFERENCE.md`, `WORLD_MODEL_README.md`; plus `backend/world_model/README.md` (fundamentals explainer) and `backend/world_model/experiments/gate_status.md` (gate ledger).
- Per-package invariants: `backend/warpsense/*/README.md` (enforced by `backend/.importlinter` — change doc and code in the same PR).
