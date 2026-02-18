"""
Pydantic schemas shared across multiple routes/services.
Import from here — never redefine these schemas elsewhere.
"""
from pydantic import BaseModel, field_validator

from models.shared_enums import WeldMetric


class MetricScore(BaseModel):
    metric: WeldMetric
    value: float  # 0.0 – 100.0
    label: str  # Human-readable display name

    @field_validator("value")
    @classmethod
    def value_in_range(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("value must be 0.0–100.0")
        return v


METRIC_LABELS: dict[WeldMetric, str] = {
    WeldMetric.ANGLE_CONSISTENCY: "Angle Consistency",
    WeldMetric.THERMAL_SYMMETRY: "Thermal Symmetry",
    WeldMetric.AMPS_STABILITY: "Amps Stability",
    WeldMetric.VOLTS_STABILITY: "Volts Stability",
    WeldMetric.HEAT_DISS_CONSISTENCY: "Heat Dissipation Consistency",
}


def make_metric_score(metric: WeldMetric, value: float) -> MetricScore:
    return MetricScore(metric=metric, value=value, label=METRIC_LABELS[metric])
