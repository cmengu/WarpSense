"""
Sites and teams CRUD endpoints.
Multi-site filtering for aggregate queries uses site_id/team_id params on existing routes.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from routes.sessions import get_db

from models.site import Site, Team
from schemas.site import SiteCreate, TeamCreate, SiteResponse, TeamResponse

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("", response_model=List[SiteResponse])
def list_sites(db: Session = Depends(get_db)):
    """List all sites with teams eager-loaded to avoid N+1 queries."""
    return (
        db.query(Site)
        .options(selectinload(Site.teams))
        .order_by(Site.name)
        .all()
    )


@router.post("", response_model=SiteResponse, status_code=201)
def create_site(body: SiteCreate, db: Session = Depends(get_db)):
    """Create a new site."""
    if db.query(Site).filter_by(id=body.id).first():
        raise HTTPException(status_code=409, detail=f"Site {body.id} already exists")
    site = Site(**body.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/{site_id}/teams", response_model=List[TeamResponse])
def list_teams(site_id: str, db: Session = Depends(get_db)):
    """List teams for a site."""
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return db.query(Team).filter_by(site_id=site_id).order_by(Team.name).all()


@router.post("/{site_id}/teams", response_model=TeamResponse, status_code=201)
def create_team(site_id: str, body: TeamCreate, db: Session = Depends(get_db)):
    """Create a team under a site. Path site_id is authoritative (ignores body.site_id)."""
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    body_data = body.model_dump()
    body_data["site_id"] = site_id  # Path is authority; ignore body.site_id
    team = Team(**body_data)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
