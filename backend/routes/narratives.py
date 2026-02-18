"""
Session narrative endpoints.
GET returns cached narrative (404 if none generated yet).
POST generates (or regenerates) and caches narrative.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from routes.sessions import get_db
from schemas.narrative import NarrativeGenerateRequest, NarrativeResponse
from services.narrative_service import get_or_generate_narrative

# Import ORM model so it registers with Base.metadata
from models.narrative import SessionNarrative  # noqa: F401

router = APIRouter(prefix="/api/sessions", tags=["narratives"])


@router.get("/{session_id}/narrative", response_model=NarrativeResponse)
def get_narrative(
    session_id: str,
    db: DBSession = Depends(get_db),
):
    """Returns cached narrative. 404 if not yet generated."""
    cached = (
        db.query(SessionNarrative).filter_by(session_id=session_id).first()
    )
    if not cached:
        raise HTTPException(
            status_code=404, detail="Narrative not yet generated"
        )
    return NarrativeResponse(
        session_id=session_id,
        narrative_text=cached.narrative_text,
        model_version=cached.model_version,
        generated_at=cached.generated_at,
        cached=True,
    )


@router.post("/{session_id}/narrative", response_model=NarrativeResponse)
def generate_narrative(
    session_id: str,
    body: NarrativeGenerateRequest,
    db: DBSession = Depends(get_db),
):
    """Generates and caches narrative. Regenerates if force_regenerate=True."""
    try:
        return get_or_generate_narrative(
            session_id, db, force_regenerate=body.force_regenerate
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
