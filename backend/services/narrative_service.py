"""
Narrative generation service.
Calls Anthropic API; caches result in session_narratives table.
Re-generates only if score changed or force_regenerate=True.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session as DBSession

from database.models import SessionModel
from models.narrative import SessionNarrative
from schemas.narrative import NarrativeResponse
from services.scoring_service import get_session_score

logger = logging.getLogger(__name__)

MODEL_ID = "claude-sonnet-4-6"
MAX_NARRATIVE_TOKENS = 600


def get_or_generate_narrative(
    session_id: str,
    db: DBSession,
    force_regenerate: bool = False,
) -> NarrativeResponse:
    """
    Returns cached narrative if available and score unchanged.
    Otherwise calls Anthropic and caches result.

    Raises:
        ValueError: Session not found.
        RuntimeError: ANTHROPIC_API_KEY not configured (503).
    """
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    current_score: float | None = (
        float(session.score_total) if session.score_total is not None else None
    )

    # Check cache
    if not force_regenerate:
        cached = (
            db.query(SessionNarrative).filter_by(session_id=session_id).first()
        )
        if cached:
            score_unchanged = (
                cached.score_snapshot is None
                or current_score is None
                or abs((cached.score_snapshot or 0) - (current_score or 0))
                < 0.01
            )
            if score_unchanged:
                return NarrativeResponse(
                    session_id=session_id,
                    narrative_text=cached.narrative_text,
                    model_version=cached.model_version,
                    generated_at=cached.generated_at,
                    cached=True,
                )

    # Build context for prompt
    context = _build_session_context(session_id, db)
    prompt = _build_prompt(context)

    # Call Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed; pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_ID,
        max_tokens=MAX_NARRATIVE_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    narrative_text = message.content[0].text.strip()

    # Upsert cache
    existing = (
        db.query(SessionNarrative).filter_by(session_id=session_id).first()
    )
    now = datetime.now(timezone.utc)
    if existing:
        existing.narrative_text = narrative_text
        existing.score_snapshot = current_score
        existing.model_version = MODEL_ID
        existing.generated_at = now
    else:
        record = SessionNarrative(
            session_id=session_id,
            narrative_text=narrative_text,
            score_snapshot=current_score,
            model_version=MODEL_ID,
        )
        db.add(record)
    db.commit()

    return NarrativeResponse(
        session_id=session_id,
        narrative_text=narrative_text,
        model_version=MODEL_ID,
        generated_at=now,
        cached=False,
    )


def _build_session_context(session_id: str, db: DBSession) -> Dict[str, Any]:
    """Pulls score, rules, and recent welder history for prompt building."""
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        return {
            "session_id": session_id,
            "weld_type": "unknown",
            "score_total": None,
            "rules": [],
            "historical_scores": [],
        }

    try:
        score = get_session_score(session_id, db)
    except ValueError:
        return {
            "session_id": session_id,
            "weld_type": session.weld_type or "unknown",
            "score_total": None,
            "rules": [],
            "historical_scores": _get_historical_scores(session, db),
        }

    rules: List[Dict[str, Any]] = [
        {
            "name": r.rule_id,
            "score": r.actual_value,
            "status": "pass" if r.passed else "fail",
        }
        for r in score.rules
    ]

    return {
        "session_id": session_id,
        "weld_type": session.weld_type or "unknown",
        "score_total": score.total,
        "rules": rules,
        "historical_scores": _get_historical_scores(session, db),
    }


def _get_historical_scores(
    session: SessionModel, db: DBSession
) -> List[float]:
    """Get last 5 score_totals for this welder (operator_id)."""
    if not session.operator_id:
        return []
    history = (
        db.query(SessionModel.score_total)
        .filter(
            SessionModel.operator_id == session.operator_id,
            SessionModel.session_id != session.session_id,
            SessionModel.score_total.isnot(None),
        )
        .order_by(SessionModel.start_time.desc())
        .limit(5)
        .all()
    )
    return [float(h.score_total) for h in history if h.score_total is not None]


def _build_prompt(ctx: Dict[str, Any]) -> str:
    """
    Builds the Anthropic prompt.
    System instructions enforce 3-paragraph structure.
    """
    historical_str = (
        ", ".join(str(round(s)) for s in ctx["historical_scores"])
        if ctx["historical_scores"]
        else "no prior sessions"
    )

    failing = [r for r in ctx["rules"] if r["status"] != "pass"]
    passing = [r for r in ctx["rules"] if r["status"] == "pass"]

    return f"""You are WarpSense, an industrial welding quality AI coach.
Write exactly 3 paragraphs for a welder performance report. Do not use headers, bullets, or markdown.

Session data:
- Weld type: {ctx['weld_type'].upper()}
- Overall score: {ctx['score_total'] or 'N/A'} / 100
- Failing rules: {', '.join(r['name'] for r in failing) or 'none'}
- Passing rules: {', '.join(r['name'] for r in passing) or 'none'}
- Recent score history: {historical_str}

Paragraph 1 (2 sentences): Overall verdict. State the score and whether the weld meets quality standards.
Paragraph 2 (2-3 sentences): Specific evidence. Reference the exact failing metrics by name and describe what they indicate physically about the weld technique.
Paragraph 3 (2 sentences): Actionable correction. Give one specific technique adjustment and state the expected improvement.

Tone: direct, technical, coach-like. No filler phrases."""
