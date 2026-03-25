# WarpSense Demo Day — 7-Day Technical Plan

**Overall Progress:** `0%` (0/11 steps done)

---

## Context

WarpSense is a production-ready multi-agent welding QC system (LangGraph + FastAPI + Next.js). The Hangar incubation judges said two blockers: no domain credibility, no pilots. The non-technical side (advisors, validation letter) is handled separately. This plan covers only the technical work that maximises demo day impact in 7 days.

**Three technical bets:**
1. **Interactive Weld Simulator** — judges adjust 3 sliders, get a defect prediction + dollar rework cost in real time. No other startup in the room will have this. (Days 2–3)
2. **Rework Cost on every analysis** — display `$4,200` / `$1,800` / `$0` prominently in the QualityReportCard so judges immediately see the business case. (Day 4)
3. **Demo stability** — model persists across restarts, 20-run smoke test catches all flaky paths, backup video recorded as safety net. (Days 1, 5–6)

---

## Architecture Overview

**What stays unchanged:** All existing routes, agents, database schema (except one `ADD COLUMN`), frontend pages, 3D visualisation, PDF export, RAG pipeline.

**What this plan adds:**
- `backend/routes/simulator.py` — new POST `/api/simulator/predict` endpoint
- `backend/ml_models/` directory + joblib model file (auto-created at startup)
- `my-app/src/app/api/warp/simulator/route.ts` — Next.js proxy route
- `my-app/src/app/(app)/simulator/page.tsx` — interactive simulator UI page
- `backend/alembic/versions/015_add_rework_cost_usd.py` — column migration
- `backend/scripts/demo_smoke_test.py` — 20-run stability script

**Critical decisions:**

| Decision | Alternative | Why rejected |
|---|---|---|
| Simulator uses existing GradientBoosting + 3 sliders + 8 fixed nominals | Call full LangGraph agent | LangGraph adds 1.5–2.8s latency per call; real-time slider feel requires <200ms |
| Rework cost is a fixed formula (DEFECTIVE=$4,200, CONDITIONAL=$1,800, PASS=$0) | Compute from violation count × labour rate | Formula is deterministic, explainable, survives judge questions |
| Model persisted with joblib on first startup | Retrain always | Restart mid-demo currently drops the classifier; joblib load takes <10ms |
| Alembic migration adds `nullable=True` column | Recreate table | Existing rows must not break; all existing `rework_cost_usd` will be NULL |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read these files in full and confirm:
(1) backend/services/warp_service.py lines 40–67: confirm init_warp_components() trains clf at line 60
(2) backend/features/weld_classifier.py lines 20–32: confirm FEATURE_COLS has exactly 11 entries in this order:
    heat_input_mean, heat_input_min_rolling, heat_input_drop_severity, heat_input_cv,
    angle_deviation_mean, angle_max_drift_1s, voltage_cv, amps_cv,
    heat_diss_mean, heat_diss_max_spike, arc_on_ratio
(3) backend/features/session_feature_extractor.py lines 25–89: confirm SessionFeatures dataclass
    has exactly these fields (excluding session_id, quality_label): same 11 as FEATURE_COLS
(4) backend/alembic/versions/: confirm latest migration file is d7f5691965bf_add_weld_quality_report_table.py
(5) my-app/src/app/(app)/layout.tsx: confirm this file exists and that it renders AppNav (confirms simulator page inside this route group will have the nav shell)
(6) my-app/src/types/warp-analysis.ts: confirm WarpReport type exists, note current fields

Do not change anything. Show full output and wait.
```

---

## PHASE 1 — Demo Pipeline Stability (Day 1)

**Goal:** Classifier survives server restart. No cold-start retrain on demo day.

---

- [ ] 🟥 **Step 1: Persist WeldClassifier with joblib** — *Critical: prevents cold-start retrain penalty*

  **Files modified:** `backend/services/warp_service.py`

  **Idempotent:** Yes — if `weld_classifier.joblib` exists, loads it; if not, trains and saves it.

  **Pre-Read Gate:**
  - `grep -n "def init_warp_components" backend/services/warp_service.py` → must return exactly 1 match
  - `grep -n "clf.train" backend/services/warp_service.py` → must return exactly 1 match inside `init_warp_components`
  - `grep -rn "joblib" backend/requirements.txt` → must confirm joblib is already a dependency

  **Change:** In `backend/services/warp_service.py`, add the two import lines to the imports section (after the existing `from features.weld_classifier import WeldClassifier` line). Then add the `_MODEL_PATH` constant on a blank line after all imports, before the existing `_graph` and `_classifier` module-level globals:

  ```python
  import joblib
  from pathlib import Path
  ```

  ```python
  _MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_models" / "weld_classifier.joblib"
  ```

  Replace the existing block (lines 57–61):
  ```python
  logger.info("warp_service: training WeldClassifier...")
  dataset = generate_feature_dataset()
  clf = WeldClassifier()
  clf.train(dataset)
  _classifier = clf
  ```

  With:
  ```python
  clf = WeldClassifier()
  if _MODEL_PATH.exists():
      saved = joblib.load(_MODEL_PATH)
      clf._model = saved["model"]
      clf._classes = saved["classes"]
      logger.info("warp_service: loaded classifier from %s", _MODEL_PATH)
  else:
      logger.info("warp_service: training WeldClassifier...")
      dataset = generate_feature_dataset()
      clf.train(dataset)
      _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
      joblib.dump({"model": clf._model, "classes": clf._classes}, _MODEL_PATH)
      logger.info("warp_service: trained and saved classifier to %s", _MODEL_PATH)
  _classifier = clf
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/services/warp_service.py
  git commit -m "step 1: persist WeldClassifier with joblib — eliminates cold-start retrain"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:** Start backend twice. Read logs both times.

  **Pass:** First start: log shows `"trained and saved classifier"` + file exists at `backend/ml_models/weld_classifier.joblib`. Second start: log shows `"loaded classifier from"` — no training occurs.

  **Fail:**
  - `RuntimeError: GROQ_API_KEY not set` → expected, not related to this step — backend still initialised
  - `AttributeError: _model` → WeldClassifier internal field name changed — grep for `self._model` in `weld_classifier.py` and update accordingly
  - `ModuleNotFoundError: joblib` → joblib not in venv — run `pip install joblib` in `backend/venv`

---

## PHASE 2 — Interactive Weld Simulator (Days 2–3)

**Goal:** `/simulator` page exists and allows a judge to adjust 3 sliders and see defect type + cost in real time.

**Slider → feature mapping (fixed):**

| Slider label | SessionFeatures field | Range | Default |
|---|---|---|---|
| Heat Input (J/frame) | `heat_input_mean` | 2000–8000 | 5500 |
| Torch Angle Deviation (°) | `angle_deviation_mean` | 0–30 | 3.0 |
| Arc Stability | `arc_on_ratio` | 0.40–1.00 | 0.92 |

**Fixed nominal values for remaining 8 features:**

| Field | Fixed value | Rationale |
|---|---|---|
| `heat_input_min_rolling` | `heat_input_mean * 0.88` | Scales with slider |
| `heat_input_drop_severity` | `180.0` | Expert baseline |
| `heat_input_cv` | `0.05` | Expert stability |
| `angle_max_drift_1s` | `angle_deviation_mean * 1.8` | Scales with slider |
| `voltage_cv` | `0.03` | Expert baseline |
| `amps_cv` | `0.04` | Expert baseline |
| `heat_diss_mean` | `2.1` | Neutral |
| `heat_diss_max_spike` | `5.0` | GOOD baseline |

**Rework cost formula:**
- `DEFECTIVE` → `$4,200`
- `MARGINAL` → `$1,800`
- `GOOD` → `$0`

**Defect type label:**
- `GOOD` → `"PASS — No Defect"`
- `MARGINAL` → `"MARGINAL — LOF Risk"`
- `DEFECTIVE` + `angle_deviation_mean > 10` → `"LOF — Lack of Fusion"`
- `DEFECTIVE` + `angle_deviation_mean ≤ 10` → `"LOP — Lack of Penetration"`

---

- [ ] 🟥 **Step 2: Backend — POST /api/simulator/predict** — *Critical: new FastAPI route*

  **New file:** `backend/routes/simulator.py`

  **Idempotent:** Yes — stateless POST endpoint with no DB writes.

  **Pre-Read Gate:**
  - `grep -n "class SessionFeatures" backend/features/session_feature_extractor.py` → must return 1 match
  - `grep -n "def get_classifier" backend/services/warp_service.py` → must return 1 match
  - Confirm `FEATURE_COLS` order matches the 11 fields in SessionFeatures.to_vector()

  ```python
  """
  POST /api/simulator/predict

  Interactive weld simulator: accepts 3 user-facing slider values, synthesises
  the remaining 8 features at expert-baseline nominals, and calls the existing
  WeldClassifier.predict(). No DB writes. No LangGraph call. ~10ms response.
  """
  from fastapi import APIRouter
  from pydantic import BaseModel, Field

  from features.session_feature_extractor import SessionFeatures
  from services.warp_service import get_classifier

  router = APIRouter(tags=["simulator"])

  _REWORK_COST: dict[str, int] = {
      "DEFECTIVE": 4200,
      "MARGINAL": 1800,
      "GOOD": 0,
  }


  class SimulatorInput(BaseModel):
      heat_input_level: float = Field(..., ge=2000.0, le=8000.0)
      torch_angle_deviation: float = Field(..., ge=0.0, le=30.0)
      arc_stability: float = Field(..., ge=0.40, le=1.00)


  class SimulatorResult(BaseModel):
      defect_type: str
      quality_class: str
      confidence: float
      rework_cost_usd: int
      top_driver: str


  @router.post("/api/simulator/predict", response_model=SimulatorResult)
  def simulator_predict(body: SimulatorInput) -> SimulatorResult:
      hi = body.heat_input_level
      ad = body.torch_angle_deviation
      ar = body.arc_stability

      features = SessionFeatures(
          session_id="simulator",
          heat_input_mean=hi,
          heat_input_min_rolling=hi * 0.88,
          heat_input_drop_severity=180.0,
          heat_input_cv=0.05,
          angle_deviation_mean=ad,
          angle_max_drift_1s=ad * 1.8,
          voltage_cv=0.03,
          amps_cv=0.04,
          heat_diss_mean=2.1,
          heat_diss_max_spike=5.0,
          arc_on_ratio=ar,
      )

      pred = get_classifier().predict(features)
      qc = pred.quality_class
      cost = _REWORK_COST.get(qc, 0)

      if qc == "GOOD":
          defect_type = "PASS — No Defect"
      elif qc == "MARGINAL":
          defect_type = "MARGINAL — LOF Risk"
      elif ad > 10:
          defect_type = "LOF — Lack of Fusion"
      else:
          defect_type = "LOP — Lack of Penetration"

      top_driver = pred.top_drivers[0][0] if pred.top_drivers else "heat_input_mean"

      return SimulatorResult(
          defect_type=defect_type,
          quality_class=qc,
          confidence=round(pred.confidence, 3),
          rework_cost_usd=cost,
          top_driver=top_driver,
      )
  ```

  **File modified:** `backend/main.py`

  Add after `from routes.warp_analysis import router as warp_analysis_router` (line 60):
  ```python
  from routes.simulator import router as simulator_router
  ```

  Add after `app.include_router(warp_analysis_router)` (line 119):
  ```python
  app.include_router(simulator_router)
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/routes/simulator.py backend/main.py
  git commit -m "step 2: add POST /api/simulator/predict — interactive weld simulator endpoint"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:**
  ```bash
  curl -s -X POST http://localhost:8000/api/simulator/predict \
    -H "Content-Type: application/json" \
    -d '{"heat_input_level": 2200, "torch_angle_deviation": 22, "arc_stability": 0.48}'
  ```

  **Pass:** Returns JSON with all 5 fields: `defect_type`, `quality_class`, `confidence`, `rework_cost_usd`, `top_driver`. `quality_class` must be `"DEFECTIVE"` or `"MARGINAL"` for these bad-weld inputs. `rework_cost_usd` must be `4200` or `1800`.

  **Fail:**
  - `404` → router not registered — confirm `app.include_router(simulator_router)` added to `main.py`
  - `422` → Pydantic validation error — check field names in request body match `SimulatorInput`
  - `RuntimeError: Classifier not trained` → `get_classifier()` returned untrained — confirm Step 1 completed and model file exists

---

- [ ] 🟥 **Step 3: Next.js proxy route** — *Critical: bridges browser → FastAPI*

  **New file:** `my-app/src/app/api/warp/simulator/route.ts`

  **Idempotent:** Yes — stateless proxy.

  **Pre-Read Gate:**
  - Read `my-app/src/app/api/warp/sessions/[sessionId]/reports/route.ts` to confirm proxy pattern (getServerBackendBaseUrl, force-dynamic, NextResponse.json)
  - Confirm `getServerBackendBaseUrl` import path used in that file

  ```typescript
  /**
   * POST /api/warp/simulator
   * Proxies to FastAPI POST /api/simulator/predict
   */
  import { NextResponse } from "next/server";
  import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

  const API_BASE = getServerBackendBaseUrl();
  export const dynamic = "force-dynamic";

  export async function POST(request: Request): Promise<NextResponse> {
    try {
      const body = await request.json();
      const res = await fetch(`${API_BASE}/api/simulator/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text.slice(0, 200) };
      }
      return NextResponse.json(data, { status: res.status });
    } catch {
      return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
    }
  }
  ```

  **Note:** Before writing, read `my-app/src/app/api/warp/sessions/[sessionId]/reports/route.ts` to confirm the exact import path for `getServerBackendBaseUrl`. Use that exact path — do not guess.

  **Git Checkpoint:**
  ```bash
  git add "my-app/src/app/api/warp/simulator/route.ts"
  git commit -m "step 3: add Next.js proxy route for weld simulator"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:** With Next.js dev server running:
  ```bash
  curl -s -X POST http://localhost:3000/api/warp/simulator \
    -H "Content-Type: application/json" \
    -d '{"heat_input_level": 5500, "torch_angle_deviation": 3, "arc_stability": 0.92}'
  ```

  **Pass:** Returns 200 with `quality_class: "GOOD"` and `rework_cost_usd: 0`.

  **Fail:**
  - `502` → backend not running or `getServerBackendBaseUrl()` pointing to wrong host
  - `404` → file path wrong — confirm directory `my-app/src/app/api/warp/simulator/` exists and file is named `route.ts`

---

- [ ] 🟥 **Step 4: TypeScript types + API helper** — *Non-critical: type safety only*

  **File modified:** `my-app/src/types/warp-analysis.ts`

  Add at the end of the file:
  ```typescript
  // Weld Simulator
  export interface SimulatorInput {
    heat_input_level: number;
    torch_angle_deviation: number;
    arc_stability: number;
  }

  export interface SimulatorResult {
    defect_type: string;
    quality_class: string;
    confidence: number;
    rework_cost_usd: number;
    top_driver: string;
  }
  ```

  **File modified:** `my-app/src/lib/warp-api.ts`

  **Pre-Read Gate:** `grep -n "from \"@/types/warp-analysis\"" my-app/src/lib/warp-api.ts` → must return exactly 1 match. Confirm the current import line is:
  ```typescript
  import type { MockSession, WarpReport, WarpHealthResponse, WelderTrendPoint } from "@/types/warp-analysis";
  ```

  Replace that line with:
  ```typescript
  import type { MockSession, WarpReport, WarpHealthResponse, WelderTrendPoint, SimulatorInput, SimulatorResult } from "@/types/warp-analysis";
  ```

  Then add at end of file (after all existing exports):
  ```typescript
  export async function simulateWeld(input: SimulatorInput): Promise<SimulatorResult> {
    const res = await fetch("/api/warp/simulator", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!res.ok) throw new Error(`simulateWeld HTTP ${res.status}`);
    return res.json() as Promise<SimulatorResult>;
  }
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/types/warp-analysis.ts my-app/src/lib/warp-api.ts
  git commit -m "step 4: add SimulatorInput/Result types and simulateWeld API helper"
  ```

  **✓ Verification:** TypeScript compilation passes — `cd my-app && npx tsc --noEmit` returns no errors related to `SimulatorInput`, `SimulatorResult`, or `simulateWeld`.

---

- [ ] 🟥 **Step 5: Simulator page UI** — *Critical: the judge-facing demo element*

  **New file:** `my-app/src/app/(app)/simulator/page.tsx`

  **Why `(app)` route group:** The `(app)/layout.tsx` wraps every page inside this group with `AppNav`. Placing the simulator here gives the nav shell automatically — no manual `AppNav.tsx` edits required.

  **Idempotent:** Yes — new file, no existing content.

  **Self-Contained Rule:** All code below is complete and immediately runnable.

  ```tsx
  "use client";

  import { useRef, useState } from "react";
  import { simulateWeld } from "@/lib/warp-api";
  import type { SimulatorResult } from "@/types/warp-analysis";

  const COST_COLOR: Record<number, string> = {
    0: "text-green-400",
    1800: "text-amber-400",
    4200: "text-red-400",
  };

  function costColor(cost: number): string {
    return COST_COLOR[cost] ?? "text-red-400";
  }

  export default function SimulatorPage() {
    const [heatInput, setHeatInput] = useState(5500);
    const [angleDeviation, setAngleDeviation] = useState(3);
    const [arcStability, setArcStability] = useState(0.92);
    const [result, setResult] = useState<SimulatorResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    async function runSimulation(hi: number, ad: number, ar: number) {
      setIsLoading(true);
      setError(null);
      try {
        const res = await simulateWeld({
          heat_input_level: hi,
          torch_angle_deviation: ad,
          arc_stability: ar,
        });
        setResult(res);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Simulation failed");
      } finally {
        setIsLoading(false);
      }
    }

    function scheduleDebounce(hi: number, ad: number, ar: number) {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => runSimulation(hi, ad, ar), 300);
    }

    function handleHeatInput(v: number) {
      setHeatInput(v);
      scheduleDebounce(v, angleDeviation, arcStability);
    }
    function handleAngle(v: number) {
      setAngleDeviation(v);
      scheduleDebounce(heatInput, v, arcStability);
    }
    function handleArc(v: number) {
      setArcStability(v);
      scheduleDebounce(heatInput, angleDeviation, v);
    }

    return (
      <main className="min-h-screen bg-zinc-950 text-zinc-100 p-8 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-1 font-mono tracking-tight">
          Weld Simulator
        </h1>
        <p className="text-zinc-400 text-sm mb-8">
          Adjust welding parameters to see real-time defect prediction.
        </p>

        <div className="space-y-6 mb-8">
          {/* Slider 1: Heat Input */}
          <div>
            <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
              <span>Heat Input (J/frame)</span>
              <span className="text-zinc-200">{heatInput.toLocaleString()}</span>
            </div>
            <input
              type="range"
              min={2000}
              max={8000}
              step={100}
              value={heatInput}
              onChange={(e) => handleHeatInput(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
              <span>2,000 (cold — LOF risk)</span>
              <span>8,000 (hot — good fusion)</span>
            </div>
          </div>

          {/* Slider 2: Torch Angle */}
          <div>
            <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
              <span>Torch Angle Deviation (°)</span>
              <span className="text-zinc-200">{angleDeviation.toFixed(1)}°</span>
            </div>
            <input
              type="range"
              min={0}
              max={30}
              step={0.5}
              value={angleDeviation}
              onChange={(e) => handleAngle(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
              <span>0° (optimal 55°)</span>
              <span>30° (extreme drift — LOF)</span>
            </div>
          </div>

          {/* Slider 3: Arc Stability */}
          <div>
            <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
              <span>Arc Stability (arc-on ratio)</span>
              <span className="text-zinc-200">{arcStability.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.40}
              max={1.00}
              step={0.01}
              value={arcStability}
              onChange={(e) => handleArc(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
              <span>0.40 (many gaps — LOF)</span>
              <span>1.00 (continuous arc)</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => runSimulation(heatInput, angleDeviation, arcStability)}
          disabled={isLoading}
          className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-500 disabled:opacity-50
                     text-white font-mono text-sm rounded-lg transition-colors mb-6"
        >
          {isLoading ? "Simulating…" : "Simulate Weld"}
        </button>

        {error && (
          <div className="p-4 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm mb-6">
            {error}
          </div>
        )}

        {result && !isLoading && (
          <div className="border border-zinc-800 rounded-xl bg-zinc-900 p-6 space-y-4">
            {/* Defect type */}
            <div>
              <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
                Defect Classification
              </p>
              <p className={`text-2xl font-bold font-mono ${
                result.quality_class === "GOOD"
                  ? "text-green-400"
                  : result.quality_class === "MARGINAL"
                  ? "text-amber-400"
                  : "text-red-400"
              }`}>
                {result.defect_type}
              </p>
            </div>

            {/* Confidence */}
            <div>
              <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
                Model Confidence
              </p>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div
                  className="bg-amber-400 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.round(result.confidence * 100)}%` }}
                />
              </div>
              <p className="text-xs text-zinc-400 mt-1 font-mono">
                {Math.round(result.confidence * 100)}%
              </p>
            </div>

            {/* Rework cost */}
            <div>
              <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
                Estimated Rework Cost
              </p>
              <p className={`text-5xl font-bold font-mono tabular-nums ${costColor(result.rework_cost_usd)}`}>
                ${result.rework_cost_usd.toLocaleString("en-US")}
              </p>
              {result.rework_cost_usd === 0 && (
                <p className="text-xs text-green-600 mt-1 font-mono">No rework required</p>
              )}
            </div>

            {/* Top driver */}
            <div>
              <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
                Top Risk Factor
              </p>
              <p className="text-sm font-mono text-zinc-300">
                {result.top_driver.replace(/_/g, " ")}
              </p>
            </div>
          </div>
        )}
      </main>
    );
  }
  ```

  **AppNav:** No changes required. The `(app)` layout already renders `AppNav` on every page inside the route group.

  **Optional polish (not required for demo day):** To add a "Simulator" item to the nav bar, read `my-app/src/components/AppNav.tsx` and follow the same `const isSimulator = pathname === '/simulator' || pathname.startsWith('/simulator')` pattern used by `isDashboard`/`isDefects`. The demo navigates to `/simulator` from the address bar — the nav link is not load-bearing.

  **Git Checkpoint:**
  ```bash
  git add "my-app/src/app/(app)/simulator/page.tsx"
  git commit -m "step 5: add interactive weld simulator page inside (app) layout"
  ```

  **✓ Verification:**

  **Type:** E2E

  **Action:** Navigate to `http://localhost:3000/simulator`.

  **Pass:**
  1. Navigate to `http://localhost:3000/simulator` — AppNav renders (confirms `(app)` layout is active)
  2. Page renders with 3 labeled sliders and current value displays
  3. Set heat input to 2000, angle to 22°, arc to 0.48 → result shows `DEFECTIVE` or `MARGINAL`, rework cost is `$4,200` or `$1,800` in red/amber
  4. Set all sliders to defaults (5500, 3, 0.92) → result shows `$0` in green

  **Fail:**
  - `Module not found: simulateWeld` → check import path in page matches `@/lib/warp-api`
  - Slider does not trigger update → confirm `onChange` calls `handleHeatInput`/etc., not `setValue` directly
  - Result card never appears → check browser console for fetch errors; confirm proxy route Step 3 is complete

---

## PHASE 3 — Rework Cost on Quality Report (Day 4)

**Goal:** Every `QualityReportCard` shows the rework cost in large font so judges immediately see the business case.

---

- [ ] 🟥 **Step 6: Alembic migration — add rework_cost_usd column** — *Critical: DB schema change*

  **New file:** `backend/alembic/versions/015_add_rework_cost_usd.py`

  **Idempotent:** No — running twice will attempt to add the same column twice. Detect with `alembic current` before running. If `015_add_rework_cost_usd` is already the head, skip this step.

  **Pre-Read Gate:**
  - Run `cd backend && alembic current` — confirm current head is `d7f5691965bf`
  - `grep -n "^revision" backend/alembic/versions/d7f5691965bf_add_weld_quality_report_table.py` → must return `revision: str = 'd7f5691965bf'` (confirms this is the latest migration, so our `down_revision = 'd7f5691965bf'` is correct)
  - Note: `down_revision` in that file is `'014_add_wqi_windowed_columns'` — do NOT grep for `down_revision`; that returns the prior migration's ID, not this one's

  ```python
  """add rework_cost_usd to weld_quality_reports

  Revision ID: 015_add_rework_cost_usd
  Revises: d7f5691965bf
  Create Date: 2026-03-24
  """
  from typing import Sequence, Union
  from alembic import op
  import sqlalchemy as sa

  revision: str = '015_add_rework_cost_usd'
  down_revision: Union[str, Sequence[str], None] = 'd7f5691965bf'
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None

  def upgrade() -> None:
      op.add_column(
          'weld_quality_reports',
          sa.Column('rework_cost_usd', sa.Integer(), nullable=True)
      )

  def downgrade() -> None:
      op.drop_column('weld_quality_reports', 'rework_cost_usd')
  ```

  Run: `cd backend && alembic upgrade head`

  **Git Checkpoint:**
  ```bash
  git add backend/alembic/versions/015_add_rework_cost_usd.py
  git commit -m "step 6: add rework_cost_usd column to weld_quality_reports (nullable)"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:** `cd backend && alembic current` → must show `015_add_rework_cost_usd (head)`.

  **Fail:**
  - `Column already exists` → migration already applied — verify with `alembic current`, skip if already head
  - `Can't locate revision d7f5691965bf` → `down_revision` wrong — grep alembic history for actual latest revision

---

- [ ] 🟥 **Step 7: Add rework_cost_usd to SQLAlchemy model + warp_service persistence** — *Critical*

  **Idempotent:** Yes — adding a column declaration to the ORM model is idempotent.

  **Files modified:** `backend/database/models.py`, `backend/services/warp_service.py`

  **Pre-Read Gate:**
  - `grep -n "WeldQualityReportModel" backend/database/models.py` → confirm class exists
  - `grep -n "agent_type" backend/database/models.py` → find insertion anchor line
  - `grep -n "WeldQualityReportModel(" backend/services/warp_service.py` → must return exactly 2 matches (lines 139 and 247)
  - `grep -n "agent_type" backend/services/warp_service.py` → find both construction sites

  **Change in `backend/database/models.py`:** Add after the `agent_type` column in `WeldQualityReportModel`:
  ```python
  rework_cost_usd = Column(Integer, nullable=True)
  ```

  **Change in `backend/services/warp_service.py`:** Add the `_REWORK_COST_BY_DISPOSITION` constant after all module-level imports and constants (after `_MODEL_PATH` added in Step 1, before `_graph` and `_classifier`):
  ```python
  _REWORK_COST_BY_DISPOSITION: dict[str, int] = {
      "REWORK_REQUIRED": 4200,
      "CONDITIONAL": 1800,
      "PASS": 0,
  }
  ```

  In **both** `WeldQualityReportModel(...)` construction sites (lines 139 and 247), add after `agent_type="langgraph",`:
  ```python
  rework_cost_usd=_REWORK_COST_BY_DISPOSITION.get(report.disposition, 0),
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/database/models.py backend/services/warp_service.py
  git commit -m "step 7: persist rework_cost_usd in WeldQualityReportModel at both construction sites"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:** Run a fresh analysis via `POST /api/sessions/sess_novice_aluminium_001_001/analyse`. Then `GET /api/sessions/sess_novice_aluminium_001_001/reports` — check the JSON response.

  **Pass:** The DB row has the value — confirm with:
  ```bash
  psql $DATABASE_URL -c "SELECT disposition, rework_cost_usd FROM weld_quality_reports WHERE session_id='sess_novice_aluminium_001_001' LIMIT 1;"
  ```
  Must return a non-null `rework_cost_usd`. Note: `$DATABASE_URL` must be set in your shell (e.g., `postgresql://postgres:password@localhost:5432/warpsense`). If not set, check `.env` or `docker-compose.yml` for the connection string and substitute directly.

  **Fail:**
  - `column "rework_cost_usd" does not exist` in psql → migration not applied — run Step 6 first
  - `AttributeError: rework_cost_usd` → column not added to SQLAlchemy model — check `models.py`

---

- [ ] 🟥 **Step 8: Expose rework_cost_usd in API response + frontend display** — *Critical: judge-facing change*

  **Files modified:** `backend/routes/warp_analysis.py`, `backend/services/warp_service.py`, `my-app/src/types/warp-analysis.ts`, `my-app/src/components/analysis/QualityReportCard.tsx`

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "rework_cost_usd\|\"disposition\"" backend/routes/warp_analysis.py` → find the GET reports response dict
  - `grep -n "WarpReport" my-app/src/types/warp-analysis.ts` → find the interface, note existing fields
  - `grep -n "Root Cause\|root_cause\|disposition_rationale" my-app/src/components/analysis/QualityReportCard.tsx` → find insertion anchor for cost display

  **Change in `backend/routes/warp_analysis.py`:** In the `get_report()` route response dict (ends with `"llm_raw_response": report_model.llm_raw_response,`), add after that line:
  ```python
  "rework_cost_usd": report_model.rework_cost_usd,
  ```

  **Change in `backend/services/warp_service.py`:** In `analyse_session_stream()`, the `complete` SSE event `queue.put_nowait(...)` dict has a `"report"` sub-dict. The last key in that sub-dict is `"llm_raw_response": report_model.llm_raw_response`. Add after it:
  ```python
  "rework_cost_usd": report_model.rework_cost_usd,
  ```
  **Anchor uniqueness check:** `grep -n "llm_raw_response.*report_model" backend/services/warp_service.py` → must return exactly 1 match (inside `_run_pipeline` / the `queue.put_nowait` block, NOT the `WeldQualityReportModel(...)` constructor). If 2+ matches, use line number to target the one inside `queue.put_nowait`.

  **Change in `my-app/src/types/warp-analysis.ts`:** In the `WarpReport` interface, add:
  ```typescript
  rework_cost_usd?: number;
  ```

  **Change in `my-app/src/components/analysis/QualityReportCard.tsx`:**

  **Anchor uniqueness check:** `grep -n "flex-1 overflow-y-auto" my-app/src/components/analysis/QualityReportCard.tsx` → must return exactly 1 match (confirmed: line 273). Insert the rework cost block as the FIRST child inside that div, before the existing `<section>` (Root Cause at line 274).

  The exact surrounding code to anchor against (lines 273–276):
  ```tsx
  <div className="flex-1 overflow-y-auto p-4 space-y-5">
    <section>
      <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
        Root Cause
  ```

  Insert the cost block between the opening `<div className="flex-1 overflow-y-auto p-4 space-y-5">` and the `<section>` (Root Cause):

  ```tsx
  {report.rework_cost_usd != null && (
    <div className="px-4 pt-3 pb-1 border-b border-zinc-900">
      <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
        Estimated Rework Cost
      </p>
      <p className={`font-mono text-3xl font-bold tabular-nums ${
        report.rework_cost_usd === 0
          ? "text-green-400"
          : report.rework_cost_usd <= 1800
          ? "text-amber-400"
          : "text-red-400"
      }`}>
        ${report.rework_cost_usd.toLocaleString("en-US")}
      </p>
      {report.rework_cost_usd === 0 && (
        <p className="font-mono text-[10px] text-green-600 mt-0.5">
          No rework required — cost avoided
        </p>
      )}
    </div>
  )}
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/routes/warp_analysis.py backend/services/warp_service.py \
    my-app/src/types/warp-analysis.ts \
    my-app/src/components/analysis/QualityReportCard.tsx
  git commit -m "step 8: expose rework_cost_usd in API response and display in QualityReportCard"
  ```

  **✓ Verification:**

  **Type:** E2E

  **Action:**
  1. Trigger fresh analysis on novice session
  2. Observe `QualityReportCard` — rework cost must appear in large font with dollar sign
  3. `GET http://localhost:8000/api/sessions/sess_novice_aluminium_001_001/reports` → JSON must contain `rework_cost_usd`

  **Pass:**
  - Novice session (REWORK_REQUIRED) shows `$4,200` in red
  - Expert session (PASS) shows `$0` in green with "No rework required" subtext
  - `rework_cost_usd` field present in raw API JSON

  **Fail:**
  - Cost block not rendered → check `report.rework_cost_usd != null` guard — confirm API is returning the field
  - `undefined` in the JSON → confirm `backend/routes/warp_analysis.py` get_report dict was updated

---

## PHASE 4 — Stress Test & Safety Net (Days 5–6)

**Goal:** Demo does not fail on stage. 20-run smoke test catches all flaky paths before demo day.

---

- [ ] 🟥 **Step 9: Demo smoke test script** — *Non-critical: test tooling*

  **New file:** `backend/scripts/demo_smoke_test.py`

  **Idempotent:** Yes — read-only against the live server.

  ```python
  """
  Demo smoke test — runs the full demo flow N times and reports pass/fail.

  Usage (from backend/):
      python -m scripts.demo_smoke_test
      python -m scripts.demo_smoke_test --runs 20 --base-url http://localhost:8000

  Exit 0 if all pass, 1 if any fail.
  """
  import argparse
  import json
  import sys
  import time
  import urllib.error
  import urllib.request

  _DEFAULT_SESSION = "sess_novice_aluminium_001_001"
  _DEFAULT_URL = "http://localhost:8000"


  def check_health(base: str) -> bool:
      try:
          r = urllib.request.urlopen(f"{base}/api/health/warp", timeout=5)
          data = json.loads(r.read())
          return bool(data.get("classifier_initialised") and data.get("graph_initialised"))
      except Exception as e:
          print(f"  health check failed: {e}")
          return False


  def run_analysis_stream(base: str, session_id: str) -> bool:
      req = urllib.request.Request(
          f"{base}/api/sessions/{session_id}/analyse",
          method="POST",
          headers={"Accept": "text/event-stream"},
      )
      try:
          with urllib.request.urlopen(req, timeout=120) as resp:
              for raw_line in resp:
                  line = raw_line.decode("utf-8").strip()
                  if not line.startswith("data:"):
                      continue
                  evt = json.loads(line[5:].strip())
                  if evt.get("stage") == "complete":
                      return "report" in evt
                  if evt.get("stage") == "error":
                      print(f"  SSE error: {evt.get('message')}")
                      return False
      except Exception as e:
          print(f"  stream error: {e}")
          return False
      return False


  def fetch_report(base: str, session_id: str) -> bool:
      try:
          r = urllib.request.urlopen(
              f"{base}/api/sessions/{session_id}/reports", timeout=10
          )
          data = json.loads(r.read())
          return "disposition" in data and "rework_cost_usd" in data
      except Exception as e:
          print(f"  report fetch failed: {e}")
          return False


  def run_simulator(base: str) -> bool:
      body = json.dumps({
          "heat_input_level": 2200,
          "torch_angle_deviation": 22,
          "arc_stability": 0.48,
      }).encode()
      req = urllib.request.Request(
          f"{base}/api/simulator/predict",
          data=body,
          method="POST",
          headers={"Content-Type": "application/json"},
      )
      try:
          r = urllib.request.urlopen(req, timeout=10)
          data = json.loads(r.read())
          return "rework_cost_usd" in data and data.get("quality_class") in ("DEFECTIVE", "MARGINAL")
      except Exception as e:
          print(f"  simulator failed: {e}")
          return False


  def main() -> None:
      parser = argparse.ArgumentParser()
      parser.add_argument("--runs", type=int, default=20)
      parser.add_argument("--base-url", default=_DEFAULT_URL)
      parser.add_argument("--session-id", default=_DEFAULT_SESSION)
      args = parser.parse_args()

      print(f"Demo smoke test: {args.runs} runs — {args.base_url}")
      print("-" * 50)

      if not check_health(args.base_url):
          print("ABORT: Backend not healthy")
          sys.exit(1)
      print("PASS health check")

      results: list[bool] = []
      for i in range(1, args.runs + 1):
          t0 = time.monotonic()
          ok_stream = run_analysis_stream(args.base_url, args.session_id)
          ok_report = fetch_report(args.base_url, args.session_id) if ok_stream else False
          ok_sim = run_simulator(args.base_url)
          elapsed = time.monotonic() - t0
          passed = ok_stream and ok_report and ok_sim
          results.append(passed)
          status = "PASS" if passed else "FAIL"
          print(
              f"  Run {i:02d}/{args.runs}: {status}"
              f"  stream={ok_stream} report={ok_report} sim={ok_sim}"
              f"  {elapsed:.1f}s"
          )

      print("-" * 50)
      passed_count = sum(results)
      print(f"Results: {passed_count}/{args.runs} passed")
      sys.exit(0 if all(results) else 1)


  if __name__ == "__main__":
      main()
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/scripts/demo_smoke_test.py
  git commit -m "step 9: add 20-run demo smoke test script"
  ```

  **✓ Verification:**

  **Type:** Integration

  **Action:** `cd backend && python -m scripts.demo_smoke_test --runs 5`

  **Pass:** All 5 runs show `PASS`. Script exits 0.

  **Fail:**
  - Any `FAIL` → read the specific check that failed (`stream=False`, `report=False`, or `sim=False`) and fix the corresponding component before running full 20-run suite

---

- [ ] 🟥 **Step 10: Run full 20-run stress test** — *Non-critical: stability validation*

  **Action (no code change):**
  ```bash
  cd backend && python -m scripts.demo_smoke_test --runs 20
  ```

  **Pass:** `Results: 20/20 passed`. Script exits 0.

  **If any fail:** Do not proceed to Step 11. Fix the failing check (identified by `stream=False`, `report=False`, or `sim=False`). Re-run until 20/20.

---

- [ ] 🟥 **Step 11: Record backup demo video** — *Non-critical: safety net*

  **Action (no code change):** With both services running locally, screen-record the 2.5-minute demo script below using QuickTime or OBS. Save as `demo_backup_YYYY-MM-DD.mp4`.

  **Demo script (click-by-click):**
  ```
  00:00  Open /demo — session browser loads
  00:08  Say: "WarpSense detects welding defects invisible to X-ray inspection."
  00:15  Point at session list — "10 sessions, expert vs novice aluminium welder."
  00:22  Navigate to /demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001
  00:28  3D torch animation plays — "Expert stays at 55°. Novice drifts to 65° — that's Lack of Fusion."
  00:50  Click "Run Analysis" on novice session
  00:55  SSE streams — "Three AI specialists analyse in parallel: Thermal, Geometry, Arc Stability."
  01:20  QualityReportCard renders — point at rework cost: "$4,200. This is what we catch."
  01:35  Click "Export PDF" — PDF downloads
  01:45  Navigate to /simulator
  01:50  Say: "Here's a perfect weld — high heat, steady angle, continuous arc. Zero cost."
  02:05  Drag heat input to 2000, angle to 22°, arc to 0.48
  02:12  Result: "$4,200 — Lack of Fusion. This is what our system prevents."
  02:30  Done.
  ```

---

## File Change Summary

| Day | New files | Modified files |
|---|---|---|
| 1 | — | `backend/services/warp_service.py` |
| 2 | `backend/routes/simulator.py`, `my-app/src/app/api/warp/simulator/route.ts` | `backend/main.py` |
| 3 | `my-app/src/app/(app)/simulator/page.tsx` | `my-app/src/types/warp-analysis.ts`, `my-app/src/lib/warp-api.ts` |
| 4 | `backend/alembic/versions/015_add_rework_cost_usd.py` | `backend/database/models.py`, `backend/services/warp_service.py`, `backend/routes/warp_analysis.py`, `my-app/src/types/warp-analysis.ts`, `my-app/src/components/analysis/QualityReportCard.tsx` |
| 5–6 | `backend/scripts/demo_smoke_test.py` | — (run 20x, fix failures) |
| 7 | — | — (record video, rehearse) |

---

## Critical Constraints for Executing Agent

1. **`FEATURE_COLS` order is sacred.** The simulator's `SessionFeatures(...)` constructor must use the exact field names from `session_feature_extractor.py` lines 25–89. Do not rename or reorder.
2. **Both `WeldQualityReportModel(...)` calls in `warp_service.py` must be updated** (lines 139 and 247). Updating only one silently drops cost data for the streaming analysis path.
3. **`rework_cost_usd` is `nullable=True`** in the migration. The TypeScript type uses `rework_cost_usd?: number` (optional). The `QualityReportCard` render is guarded by `report.rework_cost_usd != null`. Do not make it required.
4. **`alembic current` must confirm `d7f5691965bf` as head** before running migration. The new migration's `down_revision = 'd7f5691965bf'` is non-negotiable.
5. **Read the proxy route pattern** from an existing route (e.g., `my-app/src/app/api/warp/sessions/[sessionId]/reports/route.ts`) before writing Step 3. The `getServerBackendBaseUrl` import path must match exactly.
6. **Do not call `init_warp_components()` again** inside the simulator route. `get_classifier()` already has a lazy-init fallback.

---

## Success Criteria

| Feature | Verification |
|---|---|
| Model survives restart | Second startup log shows "loaded classifier from", not "training" |
| Simulator endpoint | `curl POST /api/simulator/predict` with bad-weld params → 200 + `rework_cost_usd: 4200` |
| Simulator UI | Navigate to `/simulator` → sliders update result live, `$4,200` visible in red for bad inputs |
| Rework cost in report | `GET /api/sessions/{id}/reports` → JSON contains `rework_cost_usd`; QualityReportCard shows `$` figure |
| Smoke test | `python -m scripts.demo_smoke_test --runs 20` → `20/20 passed` |
| Backup video | `demo_backup_*.mp4` file exists, 2–3 minutes, covers full demo script |
