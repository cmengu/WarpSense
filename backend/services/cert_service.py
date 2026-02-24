"""
Certification service — evaluates welder readiness against cert standards.
NO dependency on coaching_service or benchmark_service.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from database.models import SessionModel
from models.certification import CertStandard, WelderCertification
from models.session import SessionStatus
from models.shared_enums import CertificationStatus
from schemas.certification import (
    CertStandardResponse,
    CertificationStatusResponse,
    WelderCertificationSummary,
)

logger = logging.getLogger(__name__)

_STATUS_COMPLETE = SessionStatus.COMPLETE.value


def get_certification_status(
    welder_id: str, db: DBSession
) -> WelderCertificationSummary:
    """
    Evaluate welder against all cert standards; upsert welder_certifications.
    Returns summary with status, qualifying session count, and progress metrics.
    """
    standards = db.query(CertStandard).all()
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status == _STATUS_COMPLETE,
            SessionModel.score_total.isnot(None),
        )
        .order_by(SessionModel.start_time.desc())
        .all()
    )

    results = []
    for std in standards:
        relevant = [
            s
            for s in sessions
            if std.weld_type is None or s.weld_type == std.weld_type
        ]
        qualifying = [
            s for s in relevant if s.score_total >= std.required_score
        ]
        qual_count = len(qualifying)
        # relevant is non-empty here; min(len, 5) ensures divisor >= 1.
        avg_score = (
            sum(s.score_total for s in relevant[:5]) / min(len(relevant), 5)
            if relevant
            else None
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

        sessions_needed = max(0, std.sessions_required - qual_count)
        sessions_to_target = None
        if status != CertificationStatus.CERTIFIED:
            if avg_score and avg_score < std.required_score:
                gap = std.required_score - avg_score
                recent_scores = [s.score_total for s in relevant[:5]]
                if len(recent_scores) >= 2:
                    rate = (
                        recent_scores[0] - recent_scores[-1]
                    ) / len(recent_scores)
                    if rate > 0:
                        sessions_to_target = (
                            int(gap / rate) + sessions_needed
                        )

        now = datetime.now(timezone.utc)
        record = db.query(WelderCertification).filter_by(
            welder_id=welder_id, cert_standard_id=std.id
        ).first()
        if record:
            record.status = status.value
            record.evaluated_at = now
            record.qualifying_session_ids = [
                s.session_id for s in qualifying
            ]
        else:
            db.add(
                WelderCertification(
                    welder_id=welder_id,
                    cert_standard_id=std.id,
                    status=status.value,
                    evaluated_at=now,
                    qualifying_session_ids=[
                        s.session_id for s in qualifying
                    ],
                )
            )

        results.append(
            CertificationStatusResponse(
                cert_standard=CertStandardResponse.model_validate(std),
                status=status,
                evaluated_at=now,
                qualifying_sessions=qual_count,
                sessions_needed=sessions_needed,
                current_avg_score=round(avg_score, 1) if avg_score else None,
                sessions_to_target=sessions_to_target,
                qualifying_session_ids=[s.session_id for s in qualifying],
            )
        )

    db.commit()
    return WelderCertificationSummary(
        welder_id=welder_id, certifications=results
    )
