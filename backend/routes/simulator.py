"""
POST /api/simulator/predict

Interactive weld simulator: accepts 3 user-facing slider values, synthesises
the remaining 8 features at expert-baseline nominals, and calls the existing
WeldClassifier.predict(). No DB writes. No LangGraph call. ~10ms response.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from features.session_feature_extractor import SessionFeatures
from services.warp_service import get_classifier

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
