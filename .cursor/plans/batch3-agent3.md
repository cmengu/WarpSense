You are implementing the Operator Credentialing and Certification Tracking
system for a welding analytics platform in Cursor. Complete ALL steps in order.

━━━ STRICT SCOPE RULES ━━━
✅ Create or modify ONLY the files listed below
🚫 Do NOT touch: welders.py, api.ts, welder report page
🚫 Do NOT touch: any benchmark or coaching files
🚫 Do NOT import from benchmark_service or coaching_service anywhere

━━━ FILES YOU OWN (create from scratch) ━━━
- backend/alembic/versions/009_certifications.py  (fill upgrade/downgrade)
- backend/models/certification.py
- backend/schemas/certification.py
- backend/services/cert_service.py
- my-app/src/types/certification.ts
- my-app/src/components/welding/CertificationCard.tsx

━━━ FILES YOU MODIFY (partial edits only) ━━━
- backend/scripts/seed_demo_data.py   → append _seed_cert_standards() only
- my-app/src/components/pdf/WelderReportPDF.tsx    → extend props + add table section
- my-app/src/app/api/welder-report-pdf/route.ts    → extend Zod schema only

━━━ STEP 1 — Fill backend/alembic/versions/009_certifications.py ━━━

def upgrade() -> None:
    op.create_table(
        "cert_standards",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("required_score", sa.Float, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False),
        sa.Column("weld_type", sa.String(32), nullable=True),
    )
    op.create_table(
        "welder_certifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),
        sa.Column("cert_standard_id", sa.String(32),
                  sa.ForeignKey("cert_standards.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="not_started"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("qualifying_session_ids", sa.JSON, nullable=True),
        sa.UniqueConstraint("welder_id", "cert_standard_id",
                            name="uq_welder_cert"),
    )
    op.create_index("ix_welder_certifications_welder_id",
                    "welder_certifications", ["welder_id"])

def downgrade() -> None:
    op.drop_index("ix_welder_certifications_welder_id",
                  "welder_certifications")
    op.drop_table("welder_certifications")
    op.drop_table("cert_standards")

━━━ STEP 2 — Append _seed_cert_standards() to seed_demo_data.py ━━━

def _seed_cert_standards(db: Session) -> None:
    from ..models.certification import CertStandard
    STANDARDS = [
        {"id": "aws_d1_1",        "name": "AWS D1.1 Structural Welding",
         "required_score": 80.0,  "sessions_required": 3, "weld_type": None},
        {"id": "iso_9606",         "name": "ISO 9606 Welding Qualification",
         "required_score": 85.0,  "sessions_required": 4, "weld_type": None},
        {"id": "internal_basic",   "name": "Internal Basic Certification",
         "required_score": 65.0,  "sessions_required": 2, "weld_type": None},
    ]
    for s in STANDARDS:
        if not db.query(CertStandard).filter_by(id=s["id"]).first():
            db.add(CertStandard(**s))
    db.commit()

━━━ STEP 3 — Create backend/models/certification.py ━━━

from sqlalchemy import (Column, Integer, String, Float, DateTime,
                        ForeignKey, JSON, UniqueConstraint, func)
from ..database import Base

class CertStandard(Base):
    __tablename__ = "cert_standards"
    id                 = Column(String(32), primary_key=True)
    name               = Column(String(256), nullable=False)
    required_score     = Column(Float, nullable=False)
    sessions_required  = Column(Integer, nullable=False)
    weld_type          = Column(String(32), nullable=True)

class WelderCertification(Base):
    __tablename__ = "welder_certifications"
    id                    = Column(Integer, primary_key=True, autoincrement=True)
    welder_id             = Column(String(128), nullable=False)
    cert_standard_id      = Column(String(32),
                                   ForeignKey("cert_standards.id"), nullable=False)
    status                = Column(String(32), nullable=False,
                                   default="not_started")
    evaluated_at          = Column(DateTime(timezone=True),
                                   server_default=func.now(), nullable=False)
    qualifying_session_ids = Column(JSON, nullable=True)
    __table_args__ = (
        UniqueConstraint("welder_id", "cert_standard_id", name="uq_welder_cert"),
    )

━━━ STEP 4 — Create backend/schemas/certification.py ━━━

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..models.shared_enums import CertificationStatus

class CertStandardResponse(BaseModel):
    id: str
    name: str
    required_score: float
    sessions_required: int
    weld_type: Optional[str]
    class Config:
        from_attributes = True

class CertificationStatusResponse(BaseModel):
    cert_standard: CertStandardResponse
    status: CertificationStatus
    evaluated_at: datetime
    qualifying_sessions: int
    sessions_needed: int
    current_avg_score: Optional[float]
    sessions_to_target: Optional[int]
    qualifying_session_ids: Optional[List[str]]
    class Config:
        from_attributes = True

class WelderCertificationSummary(BaseModel):
    welder_id: str
    certifications: List[CertificationStatusResponse]

━━━ STEP 5 — Create backend/services/cert_service.py ━━━

"""
Certification service — evaluates welder readiness against cert standards.
NO dependency on coaching_service or benchmark_service.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession
from ..models.certification import CertStandard, WelderCertification
from ..models.session import SessionModel
from ..models.shared_enums import CertificationStatus
from ..schemas.certification import (
    CertificationStatusResponse, WelderCertificationSummary,
    CertStandardResponse
)

logger = logging.getLogger(__name__)


def get_certification_status(
    welder_id: str, db: DBSession
) -> WelderCertificationSummary:
    standards = db.query(CertStandard).all()
    sessions  = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status      == "COMPLETE",
            SessionModel.score_total.isnot(None),
        )
        .order_by(SessionModel.start_time.desc())
        .all()
    )

    results = []
    for std in standards:
        relevant   = [s for s in sessions
                      if std.weld_type is None or s.weld_type == std.weld_type]
        qualifying = [s for s in relevant if s.score_total >= std.required_score]
        qual_count = len(qualifying)
        avg_score  = (
            sum(s.score_total for s in relevant[:5]) / min(len(relevant), 5)
            if relevant else None
        )

        if qual_count >= std.sessions_required:
            status = CertificationStatus.CERTIFIED
        elif qual_count > 0:
            status = CertificationStatus.ON_TRACK
        elif avg_score and avg_score < std.required_score - 15:
            status = CertificationStatus.AT_RISK
        elif relevant:
            status = CertificationStatus.ON_TRACK
        else:
            status = CertificationStatus.NOT_STARTED

        sessions_needed  = max(0, std.sessions_required - qual_count)
        sessions_to_target = None
        if status != CertificationStatus.CERTIFIED:
            if avg_score and avg_score < std.required_score:
                gap = std.required_score - avg_score
                recent_scores = [s.score_total for s in relevant[:5]]
                if len(recent_scores) >= 2:
                    rate = (recent_scores[0] - recent_scores[-1]) / len(recent_scores)
                    if rate > 0:
                        sessions_to_target = int(gap / rate) + sessions_needed

        now    = datetime.now(timezone.utc)
        record = db.query(WelderCertification).filter_by(
            welder_id=welder_id, cert_standard_id=std.id
        ).first()
        if record:
            record.status                  = status.value
            record.evaluated_at            = now
            record.qualifying_session_ids  = [s.session_id for s in qualifying]
        else:
            db.add(WelderCertification(
                welder_id=welder_id,
                cert_standard_id=std.id,
                status=status.value,
                evaluated_at=now,
                qualifying_session_ids=[s.session_id for s in qualifying],
            ))

        results.append(CertificationStatusResponse(
            cert_standard=CertStandardResponse.model_validate(std),
            status=status,
            evaluated_at=now,
            qualifying_sessions=qual_count,
            sessions_needed=sessions_needed,
            current_avg_score=round(avg_score, 1) if avg_score else None,
            sessions_to_target=sessions_to_target,
            qualifying_session_ids=[s.session_id for s in qualifying],
        ))

    db.commit()
    return WelderCertificationSummary(welder_id=welder_id, certifications=results)

━━━ STEP 6 — Create my-app/src/types/certification.ts ━━━

import { WelderID, CertificationStatus } from "./shared";

export interface CertStandard {
  id: string;
  name: string;
  required_score: number;
  sessions_required: number;
  weld_type: string | null;
}

export interface CertificationStatusItem {
  cert_standard: CertStandard;
  status: CertificationStatus;
  evaluated_at: string;
  qualifying_sessions: number;
  sessions_needed: number;
  current_avg_score: number | null;
  sessions_to_target: number | null;
  qualifying_session_ids: string[] | null;
}

export interface WelderCertificationSummary {
  welder_id: WelderID;
  certifications: CertificationStatusItem[];
}

━━━ STEP 7 — Create my-app/src/components/welding/CertificationCard.tsx ━━━

"use client";
import React, { useEffect, useState } from "react";
import { WelderCertificationSummary, CertificationStatusItem }
  from "@/types/certification";
import { CertificationStatus, WelderID } from "@/types/shared";
import { fetchCertificationStatus } from "@/lib/api";
import { logError } from "@/lib/logger";

interface CertificationCardProps { welderId: WelderID; }

const STATUS_STYLES: Record<CertificationStatus, {
  badge: string; bar: string; icon: string;
}> = {
  certified:   { badge: "bg-green-500/10 text-green-400 border-green-500/30",
                 bar: "bg-green-500",   icon: "✓" },
  on_track:    { badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
                 bar: "bg-cyan-500",    icon: "→" },
  at_risk:     { badge: "bg-red-500/10 text-red-400 border-red-500/30",
                 bar: "bg-red-500",     icon: "⚠" },
  not_started: { badge: "bg-neutral-800 text-neutral-500 border-neutral-700",
                 bar: "bg-neutral-700", icon: "○" },
};

function CertRow({ item }: { item: CertificationStatusItem }) {
  const styles   = STATUS_STYLES[item.status];
  const progress = Math.min(100,
    (item.qualifying_sessions / item.cert_standard.sessions_required) * 100
  );

  return (
    <div className="py-3 border-b border-neutral-800 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-white">
            {item.cert_standard.name}
          </p>
          <p className="text-xs text-neutral-500 mt-0.5">
            Score ≥ {item.cert_standard.required_score}
            · {item.cert_standard.sessions_required} sessions
          </p>
        </div>
        <span className={`text-xs font-semibold uppercase px-2 py-0.5
                         rounded border ${styles.badge}`}>
          {styles.icon} {item.status.replace("_", " ")}
        </span>
      </div>
      <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden mb-1.5">
        <div
          className={`h-full rounded-full transition-all ${styles.bar}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-neutral-600">
        <span>
          {item.qualifying_sessions}/{item.cert_standard.sessions_required}
          {" "}qualifying sessions
        </span>
        {item.status === "certified" ? (
          <span className="text-green-400">Certified</span>
        ) : item.sessions_to_target ? (
          <span>~{item.sessions_to_target} sessions to cert</span>
        ) : item.current_avg_score ? (
          <span>Avg: {item.current_avg_score}/100</span>
        ) : null}
      </div>
    </div>
  );
}

export function CertificationCard({ welderId }: CertificationCardProps) {
  const [summary, setSummary] = useState<WelderCertificationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    fetchCertificationStatus(welderId)
      .then(s => { if (mounted) { setSummary(s); setLoading(false); } })
      .catch(err => {
        logError("CertificationCard", err);
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [welderId]);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest
                     text-neutral-400 mb-4">
        Certification Readiness
      </h2>
      {loading && <div className="h-32 bg-neutral-800 rounded animate-pulse" />}
      {!loading && !summary && (
        <p className="text-sm text-neutral-500">
          Unable to load certification data.
        </p>
      )}
      {!loading && summary && (
        <div>
          {summary.certifications.map(item => (
            <CertRow key={item.cert_standard.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default CertificationCard;

━━━ STEP 8 — Extend PDF (WelderReportPDF.tsx) ━━━

Open my-app/src/components/pdf/WelderReportPDF.tsx.
Extend the WelderReportPDFProps interface — add this field:

  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;

After the existing feedback items section, add:

  {certifications && certifications.length > 0 && (
    <View style={{ marginTop: 16 }}>
      <Text style={{ fontSize: 8, color: "#737373", textTransform: "uppercase",
                     letterSpacing: 1, marginBottom: 6 }}>
        Certification Readiness
      </Text>
      {certifications.map((c, i) => (
        <View key={i} style={{ flexDirection: "row",
                               justifyContent: "space-between",
                               paddingVertical: 3, borderBottomWidth: 0.5,
                               borderBottomColor: "#262626" }}>
          <Text style={{ fontSize: 9, color: "#d4d4d4" }}>
            {sanitizeText(c.name)}
          </Text>
          <Text style={{ fontSize: 9, color: "#737373" }}>
            {c.qualifying_sessions}/{c.sessions_required}
            · {sanitizeText(c.status)}
          </Text>
        </View>
      ))}
    </View>
  )}

Do NOT modify any other part of WelderReportPDF.tsx.

━━━ STEP 9 — Extend Zod schema (welder-report-pdf/route.ts) ━━━

Open my-app/src/app/api/welder-report-pdf/route.ts.
Find the Zod schema object. Add this field:

  certifications: z.array(z.object({
    name:                 z.string(),
    status:               z.string(),
    qualifying_sessions:  z.number(),
    sessions_required:    z.number(),
  })).optional().nullable(),

Do NOT modify any other part of route.ts.

━━━ VERIFICATION CHECKLIST ━━━
[ ] Migration 009 upgrade + downgrade complete with UniqueConstraint
[ ] 3 cert_standards seeded with correct thresholds
[ ] CertStandard + WelderCertification models created
[ ] cert_service.py has zero imports from coaching or benchmark
[ ] CertificationCard renders all 3 standards with correct status colours
[ ] PDF props extended + certification table section added
[ ] Zod schema extended in PDF route
[ ] welders.py NOT touched
[ ] api.ts NOT touched
[ ] welder report page NOT touched