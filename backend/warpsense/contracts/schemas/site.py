"""Pydantic schemas for Site and Team."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict

    _config_from_attributes = ConfigDict(from_attributes=True)
except ImportError:
    _config_from_attributes = None


class SiteCreate(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    location: Optional[str] = None


class TeamCreate(BaseModel):
    id: str = Field(..., min_length=1)
    site_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class TeamResponse(BaseModel):
    id: str
    site_id: str
    name: str
    created_at: datetime

    if _config_from_attributes:
        model_config = _config_from_attributes
    else:

        class Config:
            from_attributes = True


class SiteResponse(BaseModel):
    id: str
    name: str
    location: Optional[str]
    created_at: datetime
    teams: List[TeamResponse] = []

    if _config_from_attributes:
        model_config = _config_from_attributes
    else:

        class Config:
            from_attributes = True
