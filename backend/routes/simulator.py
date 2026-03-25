"""
POST /api/simulator/predict

Interactive weld simulator: accepts 3 user-facing slider values, synthesises
the remaining 8 features at expert-baseline nominals, and calls the existing
WeldClassifier.predict(). No DB writes. No LangGraph call. ~10ms response.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from features.session_feature_extractor import SessionFeatures
from services.warp_service import get_al_feature_cache, get_classifier

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


class ClosestMatchResult(BaseModel):
    session_id: str
    distance: float
    quality_class: str
    rework_cost_usd: int
    confidence: float
    matched_heat_input: float
    matched_angle_deviation: float
    matched_arc_ratio: float


@router.get("/api/simulator/closest-match", response_model=ClosestMatchResult)
def simulator_closest_match(
    heat_input_level: float = Query(..., ge=2000.0, le=8000.0),
    torch_angle_deviation: float = Query(..., ge=0.0, le=30.0),
    arc_stability: float = Query(..., ge=0.40, le=1.00),
) -> ClosestMatchResult:
    """
    Find the closest corpus session to the given simulator parameters.
    Normalized Euclidean distance on 3 features.
    Returns the matched session ID, quality prediction, and rework cost.
    """
    cache = get_al_feature_cache()
    if not cache:
        raise HTTPException(
            status_code=503,
            detail="Feature cache not yet built — restart backend",
        )

    def _nh(v: float) -> float:
        return (v - 2000.0) / 6000.0

    def _na(v: float) -> float:
        return v / 30.0

    def _nr(v: float) -> float:
        return (v - 0.40) / 0.60

    qh = _nh(heat_input_level)
    qa = _na(torch_angle_deviation)
    qr = _nr(arc_stability)

    best_id: str | None = None
    best_dist = float("inf")
    for session_id, feat in cache.items():
        dist = (
            (_nh(feat.heat_input_mean) - qh) ** 2
            + (_na(feat.angle_deviation_mean) - qa) ** 2
            + (_nr(feat.arc_on_ratio) - qr) ** 2
        ) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_id = session_id

    if best_id is None:
        raise HTTPException(status_code=503, detail="Feature cache is empty")
    matched = cache[best_id]
    pred = get_classifier().predict(matched)
    cost = _REWORK_COST.get(pred.quality_class, 0)

    return ClosestMatchResult(
        session_id=best_id,
        distance=round(best_dist, 4),
        quality_class=pred.quality_class,
        rework_cost_usd=cost,
        confidence=round(pred.confidence, 3),
        matched_heat_input=round(matched.heat_input_mean, 1),
        matched_angle_deviation=round(matched.angle_deviation_mean, 2),
        matched_arc_ratio=round(matched.arc_on_ratio, 3),
    )
