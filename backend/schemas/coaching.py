"""
Coaching schemas — drill and assignment responses for the coaching plan API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from models.shared_enums import CoachingStatus, WeldMetric


class DrillResponse(BaseModel):
    """Drill with target metric and completion criteria."""

    id: int
    target_metric: WeldMetric
    title: str
    description: str
    sessions_required: int
    success_threshold: float

    class Config:
        from_attributes = True


class CoachingAssignmentResponse(BaseModel):
    """Assignment of a drill to a welder with progress and status."""

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
    """Full coaching plan for a welder: active and completed assignments."""

    welder_id: str
    active_assignments: List[CoachingAssignmentResponse]
    completed_assignments: List[CoachingAssignmentResponse]
    auto_assigned: bool
