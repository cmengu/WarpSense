You are implementing the Automated Coaching Protocol Engine for a welding
analytics platform in Cursor. Complete ALL steps in order.

━━━ STRICT SCOPE RULES ━━━
✅ Create or modify ONLY the files listed under "Files you own"
🚫 Do NOT touch: welders.py, api.ts, welder report page
🚫 Do NOT touch: any benchmark or certification files
⚠️  DEPENDENCY RULE: coaching_service MAY import benchmark_service.
    benchmark_service must NEVER import coaching_service. Enforce this
    by keeping the benchmark_service import inside the function body
    in evaluate_progress(), not at the top of the file.

━━━ FILES YOU OWN (create from scratch) ━━━
- backend/alembic/versions/008_coaching_drills.py  (fill upgrade/downgrade)
- backend/models/coaching.py
- backend/schemas/coaching.py
- backend/services/coaching_service.py
- my-app/src/types/coaching.ts
- my-app/src/components/welding/CoachingPlanPanel.tsx

━━━ FILES YOU MODIFY (partial edits only) ━━━
- backend/scripts/seed_demo_data.py   → append _seed_drills() only
- backend/routes/sessions.py          → append evaluate_progress() call
                                        in the score handler only

━━━ STEP 1 — Fill backend/alembic/versions/008_coaching_drills.py ━━━

def upgrade() -> None:
    op.create_table(
        "drills",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("target_metric", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False,
                  server_default="3"),
        sa.Column("success_threshold", sa.Float, nullable=False,
                  server_default="70.0"),
    )
    op.create_table(
        "coaching_assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),
        sa.Column("drill_id", sa.Integer, sa.ForeignKey("drills.id"),
                  nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="active"),
        sa.Column("sessions_completed", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_coaching_assignments_welder_id",
                    "coaching_assignments", ["welder_id"])
    op.create_index("ix_coaching_assignments_status",
                    "coaching_assignments", ["status"])

def downgrade() -> None:
    op.drop_index("ix_coaching_assignments_status", "coaching_assignments")
    op.drop_index("ix_coaching_assignments_welder_id", "coaching_assignments")
    op.drop_table("coaching_assignments")
    op.drop_table("drills")

━━━ STEP 2 — Append _seed_drills() to seed_demo_data.py ━━━

Add SEED_DRILLS list (12 drills across 5 metrics) and _seed_drills().
Guard: if db.query(Drill).count() >= len(SEED_DRILLS): return

SEED_DRILLS = [
  # angle_consistency
  {"target_metric": "angle_consistency",
   "title": "30-45-60 Angle Progression",
   "description": "Practice at 30°, 45°, and 60° for 5 minutes each. Focus on wrist stability. Use a guide block to feel the target angle before removing it.",
   "sessions_required": 3, "success_threshold": 75.0},
  {"target_metric": "angle_consistency",
   "title": "Slow-Motion Angle Hold",
   "description": "Weld at half normal travel speed. Prioritise holding the torch angle constant over travel speed. Record 3 sessions.",
   "sessions_required": 3, "success_threshold": 72.0},
  {"target_metric": "angle_consistency",
   "title": "Angle Awareness Drill",
   "description": "Before each weld, verbally state the target angle. After each weld, estimate the actual average angle and compare to readout.",
   "sessions_required": 2, "success_threshold": 70.0},
  # thermal_symmetry
  {"target_metric": "thermal_symmetry",
   "title": "Reduced Travel Speed",
   "description": "Drop travel speed by 20%. Slower travel distributes heat more evenly across the joint width. Monitor N-S symmetry gauge.",
   "sessions_required": 3, "success_threshold": 75.0},
  {"target_metric": "thermal_symmetry",
   "title": "Centreline Focus",
   "description": "Place a chalk line on the workpiece and keep the torch tip within 2mm of it throughout the weld.",
   "sessions_required": 2, "success_threshold": 70.0},
  {"target_metric": "thermal_symmetry",
   "title": "Pre-heat Pattern Practice",
   "description": "Apply pre-heat in a symmetrical pattern before welding. Verify N-S and E-W temps are within 5°C before starting.",
   "sessions_required": 2, "success_threshold": 72.0},
  # amps_stability
  {"target_metric": "amps_stability",
   "title": "Steady Contact Distance",
   "description": "Maintain consistent contact tip to work distance. Use a feeler gauge (12mm) to calibrate starting position before each run.",
   "sessions_required": 3, "success_threshold": 75.0},
  {"target_metric": "amps_stability",
   "title": "Voltage-Amps Coupling Check",
   "description": "Verify machine settings match material spec sheet before each session. Check for worn contact tips.",
   "sessions_required": 2, "success_threshold": 70.0},
  # volts_stability
  {"target_metric": "volts_stability",
   "title": "Arc Length Consistency",
   "description": "Focus on maintaining constant arc length by watching the weld pool width. Practice on scrap for 10 minutes first.",
   "sessions_required": 3, "success_threshold": 75.0},
  {"target_metric": "volts_stability",
   "title": "Travel Speed Uniformity",
   "description": "Use a metronome (80 BPM) to set travel rhythm. Consistent speed prevents voltage spikes from sudden pauses.",
   "sessions_required": 2, "success_threshold": 70.0},
  # heat_diss_consistency
  {"target_metric": "heat_diss_consistency",
   "title": "Cool-Down Interval Protocol",
   "description": "Add 30-second intervals between passes. Monitor center temp; do not start next pass until below 200°C.",
   "sessions_required": 3, "success_threshold": 70.0},
  {"target_metric": "heat_diss_consistency",
   "title": "Backstepping Technique",
   "description": "Practice backstep welding pattern (weld right-to-left in segments). Reduces cumulative heat buildup.",
   "sessions_required": 3, "success_threshold": 72.0},
]

def _seed_drills(db: Session) -> None:
    from ..models.coaching import Drill
    if db.query(Drill).count() >= len(SEED_DRILLS):
        return
    for d in SEED_DRILLS:
        db.add(Drill(**d))
    db.commit()

━━━ STEP 3 — Create backend/models/coaching.py ━━━

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, func
from ..database import Base

class Drill(Base):
    __tablename__ = "drills"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    target_metric     = Column(String(64), nullable=False)
    title             = Column(String(256), nullable=False)
    description       = Column(Text, nullable=False)
    sessions_required = Column(Integer, nullable=False, default=3)
    success_threshold = Column(Float, nullable=False, default=70.0)

class CoachingAssignment(Base):
    __tablename__ = "coaching_assignments"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    welder_id          = Column(String(128), nullable=False)
    drill_id           = Column(Integer, ForeignKey("drills.id"), nullable=False)
    assigned_at        = Column(DateTime(timezone=True),
                                server_default=func.now(), nullable=False)
    status             = Column(String(32), nullable=False, default="active")
    sessions_completed = Column(Integer, nullable=False, default=0)
    completed_at       = Column(DateTime(timezone=True), nullable=True)

━━━ STEP 4 — Create backend/schemas/coaching.py ━━━

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..models.shared_enums import WeldMetric, CoachingStatus

class DrillResponse(BaseModel):
    id: int
    target_metric: WeldMetric
    title: str
    description: str
    sessions_required: int
    success_threshold: float
    class Config:
        from_attributes = True

class CoachingAssignmentResponse(BaseModel):
    id: int
    welder_id: str
    drill: DrillResponse
    assigned_at: datetime
    status: CoachingStatus
    sessions_completed: int
    completed_at: Optional[datetime]
    current_metric_value: Optional[float] = None
    class Config:
        from_attributes = True

class CoachingPlanResponse(BaseModel):
    welder_id: str
    active_assignments: List[CoachingAssignmentResponse]
    completed_assignments: List[CoachingAssignmentResponse]
    auto_assigned: bool

━━━ STEP 5 — Create backend/services/coaching_service.py ━━━

"""
Coaching service — drill assignment and progress evaluation.

DEPENDENCY RULE:
  coaching_service → benchmark_service (one-way only, lazy import in fn body)
  benchmark_service must NEVER import coaching_service.

Constants:
  AUTO_ASSIGN_THRESHOLD = 60.0
  MAX_ACTIVE_ASSIGNMENTS = 2
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession
from ..models.coaching import Drill, CoachingAssignment
from ..models.shared_enums import CoachingStatus
from ..schemas.coaching import (
    CoachingPlanResponse, CoachingAssignmentResponse, DrillResponse
)
from ..schemas.benchmark import WelderBenchmarks

logger = logging.getLogger(__name__)
AUTO_ASSIGN_THRESHOLD  = 60.0
MAX_ACTIVE_ASSIGNMENTS = 2


def get_coaching_plan(welder_id: str, db: DBSession) -> CoachingPlanResponse:
    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )
    completed = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "complete")
        .order_by(CoachingAssignment.completed_at.desc())
        .limit(10).all()
    )

    def enrich(assignment: CoachingAssignment) -> CoachingAssignmentResponse:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        return CoachingAssignmentResponse(
            id=assignment.id,
            welder_id=assignment.welder_id,
            drill=DrillResponse.model_validate(drill),
            assigned_at=assignment.assigned_at,
            status=CoachingStatus(assignment.status),
            sessions_completed=assignment.sessions_completed,
            completed_at=assignment.completed_at,
        )

    return CoachingPlanResponse(
        welder_id=welder_id,
        active_assignments=[enrich(a) for a in active],
        completed_assignments=[enrich(a) for a in completed],
        auto_assigned=False,
    )


def assign_coaching_plan(
    welder_id: str,
    benchmark_data: WelderBenchmarks,
    db: DBSession,
) -> CoachingPlanResponse:
    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )
    if len(active) >= MAX_ACTIVE_ASSIGNMENTS:
        plan = get_coaching_plan(welder_id, db)
        plan.auto_assigned = False
        return plan

    covered_metrics = set()
    for a in active:
        drill = db.query(Drill).filter_by(id=a.drill_id).first()
        if drill:
            covered_metrics.add(drill.target_metric)

    worst_metrics = sorted(
        [m for m in benchmark_data.metrics
         if m.metric.value not in covered_metrics],
        key=lambda m: m.percentile,
    )

    new_assignments = 0
    for bm in worst_metrics:
        if new_assignments + len(active) >= MAX_ACTIVE_ASSIGNMENTS:
            break
        if bm.percentile >= 50:
            continue
        drill = (
            db.query(Drill)
            .filter_by(target_metric=bm.metric.value)
            .order_by(Drill.success_threshold.asc())
            .first()
        )
        if not drill:
            continue
        db.add(CoachingAssignment(
            welder_id=welder_id, drill_id=drill.id,
            status="active", sessions_completed=0,
        ))
        new_assignments += 1

    if new_assignments > 0:
        db.commit()

    plan = get_coaching_plan(welder_id, db)
    plan.auto_assigned = new_assignments > 0
    return plan


def evaluate_progress(welder_id: str, db: DBSession) -> int:
    # Lazy import to prevent circular dependency at module load time
    from ..services.benchmark_service import get_welder_benchmarks

    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )
    if not active:
        return 0

    benchmarks    = get_welder_benchmarks(welder_id, db)
    metric_values = {m.metric.value: m.welder_value for m in benchmarks.metrics}
    completed     = 0

    for assignment in active:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        if not drill:
            continue
        assignment.sessions_completed += 1
        current_val = metric_values.get(drill.target_metric, 0.0)
        if current_val >= drill.success_threshold:
            assignment.status      = "complete"
            assignment.completed_at = datetime.now(timezone.utc)
            completed += 1

    db.commit()
    return completed

━━━ STEP 6 — Append evaluate_progress call to sessions.py score handler ━━━

Find the GET score handler in backend/routes/sessions.py.
After the block that persists score_total to the session, append:

    from ..services.coaching_service import evaluate_progress
    if session.operator_id:
        try:
            evaluate_progress(session.operator_id, db)
        except Exception as e:
            logger.warning(
                "evaluate_progress failed for %s: %s",
                session.operator_id, e
            )
            # Non-critical — do not re-raise

Do NOT modify any other part of sessions.py.

━━━ STEP 7 — Create my-app/src/types/coaching.ts ━━━

import { WelderID, WeldMetric, CoachingStatus } from "./shared";

export interface Drill {
  id: number;
  target_metric: WeldMetric;
  title: string;
  description: string;
  sessions_required: number;
  success_threshold: number;
}

export interface CoachingAssignment {
  id: number;
  welder_id: WelderID;
  drill: Drill;
  assigned_at: string;
  status: CoachingStatus;
  sessions_completed: number;
  completed_at: string | null;
  current_metric_value: number | null;
}

export interface CoachingPlan {
  welder_id: WelderID;
  active_assignments: CoachingAssignment[];
  completed_assignments: CoachingAssignment[];
  auto_assigned: boolean;
}

━━━ STEP 8 — Create my-app/src/components/welding/CoachingPlanPanel.tsx ━━━

"use client";
import React, { useEffect, useState } from "react";
import { CoachingPlan, CoachingAssignment } from "@/types/coaching";
import { METRIC_LABELS, WelderID } from "@/types/shared";
import { fetchCoachingPlan, triggerCoachingAssignment } from "@/lib/api";
import { logError } from "@/lib/logger";

interface CoachingPlanPanelProps { welderId: WelderID; }

function AssignmentCard({ a }: { a: CoachingAssignment }) {
  const pct = a.current_metric_value !== null
    ? Math.min(100, (a.current_metric_value / a.drill.success_threshold) * 100)
    : null;

  const statusColor = {
    active:   "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
    complete: "text-green-400 border-green-500/30 bg-green-500/5",
    overdue:  "text-red-400 border-red-500/30 bg-red-500/5",
  }[a.status];

  return (
    <div className={`rounded-lg border p-4 ${statusColor}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-semibold text-white">{a.drill.title}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {METRIC_LABELS[a.drill.target_metric]}
            · {a.sessions_completed}/{a.drill.sessions_required} sessions
          </p>
        </div>
        <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded
                         ${statusColor}`}>
          {a.status}
        </span>
      </div>
      <p className="text-xs text-neutral-400 leading-relaxed mb-3">
        {a.drill.description}
      </p>
      {pct !== null && (
        <div>
          <div className="flex justify-between text-xs text-neutral-500 mb-1">
            <span>Progress to target ({Math.round(a.drill.success_threshold)})</span>
            <span>{Math.round(pct)}%</span>
          </div>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-500 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}
      {a.status === "complete" && (
        <p className="text-xs text-green-400 mt-2">
          ✓ Drill complete
          · {a.completed_at ? new Date(a.completed_at).toLocaleDateString() : ""}
        </p>
      )}
    </div>
  );
}

export function CoachingPlanPanel({ welderId }: CoachingPlanPanelProps) {
  const [plan, setPlan]         = useState<CoachingPlan | null>(null);
  const [loading, setLoading]   = useState(true);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetchCoachingPlan(welderId)
      .then(p => { if (mounted) { setPlan(p); setLoading(false); } })
      .catch(err => { logError("CoachingPlanPanel", err);
                      if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [welderId]);

  const handleAssign = async () => {
    setAssigning(true);
    try {
      setPlan(await triggerCoachingAssignment(welderId));
    } catch (err) {
      logError("CoachingPlanPanel.handleAssign", err);
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Coaching Plan
        </h2>
        {!loading && (
          <button
            onClick={handleAssign} disabled={assigning}
            className="text-xs text-cyan-400 hover:text-cyan-300
                       underline disabled:text-neutral-600"
          >
            {assigning ? "Assigning…" : "Assign Drills"}
          </button>
        )}
      </div>
      {loading && <div className="h-24 bg-neutral-800 rounded animate-pulse" />}
      {!loading && plan && (
        <>
          {plan.auto_assigned && (
            <div className="text-xs text-cyan-400 bg-cyan-500/10 border
                            border-cyan-500/20 rounded px-3 py-2 mb-3">
              New drills assigned based on your latest benchmarks.
            </div>
          )}
          {plan.active_assignments.length === 0 ? (
            <p className="text-sm text-neutral-500 text-center py-4">
              No active drills. Click "Assign Drills" to get recommendations.
            </p>
          ) : (
            <div className="space-y-3">
              {plan.active_assignments.map(a => (
                <AssignmentCard key={a.id} a={a} />
              ))}
            </div>
          )}
          {plan.completed_assignments.length > 0 && (
            <details className="mt-4">
              <summary className="text-xs text-neutral-600 cursor-pointer
                                  hover:text-neutral-400">
                {plan.completed_assignments.length} completed drill(s)
              </summary>
              <div className="space-y-2 mt-2">
                {plan.completed_assignments.map(a => (
                  <AssignmentCard key={a.id} a={a} />
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}

export default CoachingPlanPanel;

━━━ VERIFICATION CHECKLIST ━━━
[ ] Migration 008 upgrade + downgrade complete with both indexes
[ ] 12 drills seeded across all 5 metrics
[ ] Drill + CoachingAssignment models created
[ ] coaching_service has NO top-level import of benchmark_service
[ ] evaluate_progress() uses lazy import inside function body
[ ] evaluate_progress() wired non-fatally into sessions.py score handler
[ ] CoachingPlanPanel renders active drills with progress bars
[ ] Assign Drills button calls POST and updates state
[ ] welders.py NOT touched
[ ] api.ts NOT touched
[ ] welder report page NOT touched