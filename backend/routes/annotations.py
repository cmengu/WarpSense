"""
Annotation endpoints.
Session-scoped: POST/GET /api/sessions/{session_id}/annotations
Cross-session defect library: GET /api/defects
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database.models import SessionModel
from models.annotation import SessionAnnotation
from models.shared_enums import AnnotationType
from routes.sessions import get_db
from schemas.annotation import (
    AnnotationCreate,
    AnnotationResponse,
    DefectLibraryItem,
)

router = APIRouter(prefix="/api", tags=["annotations"])


@router.post(
    "/sessions/{session_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation(
    session_id: str,
    body: AnnotationCreate,
    db: DBSession = Depends(get_db),
):
    """Create an annotation at a given timestamp.
    Returns 404 if session not found.
    Returns 201 with AnnotationResponse on success.
    """
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    ann = SessionAnnotation(
        session_id=session_id,
        timestamp_ms=body.timestamp_ms,
        annotation_type=body.annotation_type.value,
        note=body.note,
        created_by=body.created_by,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.get(
    "/sessions/{session_id}/annotations",
    response_model=List[AnnotationResponse],
)
def get_session_annotations(
    session_id: str,
    db: DBSession = Depends(get_db),
):
    """Return annotations for a session. 404 if session not found."""
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    annotations = (
        db.query(SessionAnnotation)
        .filter_by(session_id=session_id)
        .order_by(SessionAnnotation.timestamp_ms.asc())
        .all()
    )
    return annotations


# TODO: weld_type filter exists; defects page UI does not yet expose it.
@router.get("/defects", response_model=List[DefectLibraryItem])
def get_defect_library(
    annotation_type: Optional[AnnotationType] = Query(None),
    weld_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: DBSession = Depends(get_db),
):
    """
    Cross-session defect library.
    Returns confirmed/near-miss annotations with session metadata.
    """
    q = (
        db.query(SessionAnnotation, SessionModel)
        .join(
            SessionModel,
            SessionModel.session_id == SessionAnnotation.session_id,
        )
    )
    if annotation_type is not None:
        q = q.filter(SessionAnnotation.annotation_type == annotation_type.value)
    if weld_type:
        q = q.filter(SessionModel.weld_type == weld_type)

    rows = q.order_by(SessionAnnotation.created_at.desc()).limit(limit).all()

    result = []
    for ann, sess in rows:
        result.append(
            DefectLibraryItem(
                id=ann.id,
                session_id=ann.session_id,
                timestamp_ms=ann.timestamp_ms,
                annotation_type=ann.annotation_type,
                note=ann.note,
                created_by=ann.created_by,
                created_at=ann.created_at,
                weld_type=sess.weld_type,
                operator_id=sess.operator_id,
            )
        )
    return result
