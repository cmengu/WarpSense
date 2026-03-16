"""
eval_scenarios.py
-----------------
24 deterministic eval scenarios for WarpSense pipeline testing.

Each scenario constructs a SessionFeatures with specific fixed values,
runs the full agent pipeline, and compares the output disposition to
the expected label.

No randomness. No mock generators. Fully reproducible.

Scenario categories:
  TRUE_REWORK  (8) — pipeline must fire REWORK_REQUIRED
  TRUE_PASS    (8) — pipeline must NOT fire, PASS expected
  FP_RISK      (4) — CONDITIONAL expected, not REWORK (over-firing risk)
  FN_RISK      (4) — floor/boundary cases that must NOT be missed

Usage:
    from backend.eval.eval_scenarios import SCENARIOS, BASE_EXPERT_FEATURES
"""

from dataclasses import dataclass
from typing import Optional
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.features.session_feature_extractor import SessionFeatures


# ─────────────────────────────────────────────────────────────────────────────
# BASE EXPERT FEATURE VALUES
# All values safely inside GOOD band per THRESHOLDS in warpsense_agent.py.
# Scenarios override only the features relevant to the test case.
# ─────────────────────────────────────────────────────────────────────────────

BASE_EXPERT_FEATURES = {
    "heat_input_mean": 5200.0,  # GOOD: > 4500
    "heat_input_min_rolling": 4200.0,  # GOOD: > 4000
    "heat_input_drop_severity": 7.0,  # GOOD: < 10
    "heat_input_cv": 0.07,  # GOOD: < 0.10
    "angle_deviation_mean": 4.0,  # GOOD: < 8
    "angle_max_drift_1s": 6.0,  # GOOD: < 10
    "voltage_cv": 0.05,  # GOOD: < 0.08
    "amps_cv": 0.05,  # GOOD: < 0.08
    "heat_diss_mean": 1.2,  # GOOD: low
    "heat_diss_max_spike": 4.0,  # GOOD: < 10
    "arc_on_ratio": 0.93,  # GOOD: > 0.90
}


def make_features(
    session_id: str, overrides: dict, quality_label: Optional[str] = None
) -> SessionFeatures:
    vals = {**BASE_EXPERT_FEATURES, **overrides}
    return SessionFeatures(
        session_id=session_id,
        heat_input_mean=vals["heat_input_mean"],
        heat_input_min_rolling=vals["heat_input_min_rolling"],
        heat_input_drop_severity=vals["heat_input_drop_severity"],
        heat_input_cv=vals["heat_input_cv"],
        angle_deviation_mean=vals["angle_deviation_mean"],
        angle_max_drift_1s=vals["angle_max_drift_1s"],
        voltage_cv=vals["voltage_cv"],
        amps_cv=vals["amps_cv"],
        heat_diss_mean=vals["heat_diss_mean"],
        heat_diss_max_spike=vals["heat_diss_max_spike"],
        arc_on_ratio=vals["arc_on_ratio"],
        quality_label=quality_label,
    )


# ─────────────────────────────────────────────────────────────────────────────
# EVAL SCENARIO DATACLASS
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class EvalScenario:
    scenario_id: str
    description: str
    category: str  # TRUE_REWORK | TRUE_PASS | FP_RISK | FN_RISK
    features: SessionFeatures
    expected_disposition: str  # PASS | CONDITIONAL | REWORK_REQUIRED
    tolerance: str = "DISPOSITION_ONLY"
    # DISPOSITION_ONLY:  only disposition checked (LLM output varies between runs)
    # EXACT:             disposition AND iso_5817_level must match — enforcement in Phase 6
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS: list[EvalScenario] = [
    # ── TRUE_REWORK (8) ───────────────────────────────────────────────────────
    EvalScenario(
        scenario_id="TC_001_novice_classic",
        description="Classic novice profile — high thermal spike + high angle drift",
        category="TRUE_REWORK",
        features=make_features(
            "TC_001",
            {
                "heat_diss_max_spike": 65.0,  # RISK: > 40
                "angle_deviation_mean": 20.0,  # RISK: > 15
                "heat_input_min_rolling": 3200.0,  # RISK: < 3500
                "heat_input_drop_severity": 17.0,  # RISK: > 15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Mirrors the novice benchmark from Phase 1. All 4 LOF features in RISK.",
    ),
    EvalScenario(
        scenario_id="TC_002_thermal_spike_only",
        description="Thermal spike only — all other features at expert baseline",
        category="TRUE_REWORK",
        features=make_features(
            "TC_002",
            {
                "heat_diss_max_spike": 45.0,  # RISK: > 40
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Single-feature RISK. Tests that thermal spike alone triggers REWORK.",
    ),
    EvalScenario(
        scenario_id="TC_003_angle_drift_only",
        description="Angle drift only — all other features at expert baseline",
        category="TRUE_REWORK",
        features=make_features(
            "TC_003",
            {
                "angle_deviation_mean": 22.0,  # RISK: > 15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Single-feature RISK. Tests that angle drift alone triggers REWORK.",
    ),
    EvalScenario(
        scenario_id="TC_004_cold_window_lop_risk",
        description="Cold arc window — heat_input_min_rolling in RISK band (LOP risk)",
        category="TRUE_REWORK",
        features=make_features(
            "TC_004",
            {
                "heat_input_min_rolling": 2000.0,  # RISK: < 3500
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="LOP primary signal. Tests cold arc window detection independently.",
    ),
    EvalScenario(
        scenario_id="TC_005_all_lof_features_at_risk_floor",
        description="All 4 LOF features at exactly marginal_max + 0.1 (boundary RISK entry)",
        category="TRUE_REWORK",
        features=make_features(
            "TC_005",
            {
                "heat_diss_max_spike": 40.1,  # RISK: > 40
                "angle_deviation_mean": 15.1,  # RISK: > 15
                "heat_input_min_rolling": 3499.9,  # RISK: < 3500
                "heat_input_drop_severity": 15.1,  # RISK: > 15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="All 4 LOF features just inside RISK band. Tests boundary precision.",
    ),
    EvalScenario(
        scenario_id="TC_006_compound_process_instability",
        description="Compound instability — high heat_input_cv + high voltage_cv",
        category="TRUE_REWORK",
        features=make_features(
            "TC_006",
            {
                "heat_input_cv": 0.30,  # RISK: > 0.20
                "voltage_cv": 0.18,  # RISK: > 0.15
                "amps_cv": 0.15,  # RISK: > 0.12
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="heat_input_cv in RISK maps to LOF — triggers hard override to REWORK.",
    ),
    EvalScenario(
        scenario_id="TC_007_low_arc_continuity",
        description="Very low arc-on ratio — excessive arc interruptions",
        category="TRUE_REWORK",
        features=make_features(
            "TC_007",
            {
                "arc_on_ratio": 0.55,  # RISK: < 0.75
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Each arc restart is a cold-start LOF risk. arc_on_ratio=0.55 is extreme.",
    ),
    EvalScenario(
        scenario_id="TC_008_heat_drop_severity_risk",
        description="heat_input_drop_severity just inside RISK band",
        category="TRUE_REWORK",
        features=make_features(
            "TC_008",
            {
                "heat_input_drop_severity": 15.5,  # RISK: > 15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Stitch transition severity in RISK. LOF at every restart boundary.",
    ),
    # ── TRUE_PASS (8) ─────────────────────────────────────────────────────────
    # All features inside GOOD band. Disposition must be PASS.
    # NOTE: heat_input_min_rolling uses 4200.0 (not 3982 — that value is MARGINAL).
    # NOTE: arc_on_ratio uses 0.91 (not 0.88 — that value is MARGINAL).
    EvalScenario(
        scenario_id="TC_009_expert_benchmark_exact",
        description="Expert benchmark profile — all features in GOOD band",
        category="TRUE_PASS",
        features=make_features(
            "TC_009",
            {
                "heat_diss_max_spike": 3.6,
                "angle_deviation_mean": 4.0,
                "heat_input_min_rolling": 4200.0,  # GOOD: > 4000
                "heat_input_drop_severity": 9.8,
                "heat_input_mean": 5500.0,
                "heat_input_cv": 0.07,
                "voltage_cv": 0.05,
                "amps_cv": 0.05,
                "arc_on_ratio": 0.93,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Expert benchmark profile. heat_input_min_rolling=4200 (GOOD band — Phase 1 raw value 3982 sits in MARGINAL).",
    ),
    EvalScenario(
        scenario_id="TC_010_all_features_good_band_boundary",
        description="All features at GOOD band boundary — just inside threshold",
        category="TRUE_PASS",
        features=make_features(
            "TC_010",
            {
                "heat_diss_max_spike": 9.9,  # GOOD: < 10
                "angle_deviation_mean": 7.9,  # GOOD: < 8
                "heat_input_min_rolling": 4001.0,  # GOOD: > 4000
                "heat_input_drop_severity": 9.9,  # GOOD: < 10
                "heat_input_cv": 0.09,  # GOOD: < 0.10
                "voltage_cv": 0.07,  # GOOD: < 0.08
                "amps_cv": 0.07,  # GOOD: < 0.08
                "arc_on_ratio": 0.901,  # GOOD: > 0.90
                "heat_input_mean": 4501.0,  # GOOD: > 4500
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Boundary -0.1 case. Tests that good-band boundary does not trigger.",
    ),
    EvalScenario(
        scenario_id="TC_011_thermal_spike_below_threshold",
        description="heat_diss_max_spike at 9.9 — one unit below GOOD threshold",
        category="TRUE_PASS",
        features=make_features(
            "TC_011",
            {
                "heat_diss_max_spike": 9.9,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Single-feature boundary below GOOD threshold. Must not trigger.",
    ),
    EvalScenario(
        scenario_id="TC_012_angle_deviation_below_threshold",
        description="angle_deviation_mean at 7.9 — one unit below GOOD threshold",
        category="TRUE_PASS",
        features=make_features(
            "TC_012",
            {
                "angle_deviation_mean": 7.9,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Single-feature boundary below GOOD threshold. Must not trigger.",
    ),
    EvalScenario(
        scenario_id="TC_013_hot_but_controlled",
        description="High heat input but all consistency metrics GOOD",
        category="TRUE_PASS",
        features=make_features(
            "TC_013",
            {
                "heat_input_mean": 8000.0,
                "heat_input_cv": 0.05,
                "heat_diss_mean": 3.0,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="High heat input is not dangerous — only low heat input is RISK.",
    ),
    EvalScenario(
        scenario_id="TC_014_stitch_expert_profile",
        description="Stitch expert profile — controlled restarts, all features GOOD",
        category="TRUE_PASS",
        features=make_features(
            "TC_014",
            {
                "heat_input_drop_severity": 9.5,  # GOOD: < 10
                "arc_on_ratio": 0.91,  # GOOD: > 0.90 — stitch pauses captured by drop_severity, not arc_on_ratio
                "heat_input_min_rolling": 4100.0,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="arc_on_ratio=0.91 (GOOD). Stitch pauses are captured by heat_input_drop_severity=9.5.",
    ),
    EvalScenario(
        scenario_id="TC_015_continuous_expert_arc",
        description="Very high arc continuity — near-perfect continuous pass",
        category="TRUE_PASS",
        features=make_features(
            "TC_015",
            {
                "arc_on_ratio": 0.97,
                "heat_input_cv": 0.04,
                "voltage_cv": 0.03,
                "amps_cv": 0.03,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Ideal continuous pass. All stability metrics at floor.",
    ),
    EvalScenario(
        scenario_id="TC_016_minimal_variance_process",
        description="Extremely consistent process — all CV metrics at floor",
        category="TRUE_PASS",
        features=make_features(
            "TC_016",
            {
                "heat_input_cv": 0.02,
                "voltage_cv": 0.02,
                "amps_cv": 0.02,
                "heat_diss_max_spike": 2.0,
                "angle_deviation_mean": 2.0,
            },
            quality_label="GOOD",
        ),
        expected_disposition="PASS",
        notes="Robotic-quality consistency. Baseline sanity check for PASS.",
    ),
    # ── FP_RISK (4) ───────────────────────────────────────────────────────────
    # MARGINAL band features only — no RISK band LOF/LOP features.
    # Expected: CONDITIONAL (not REWORK_REQUIRED).
    EvalScenario(
        scenario_id="TC_017_heat_input_mean_marginal",
        description="heat_input_mean in MARGINAL band — cold weld but not RISK",
        category="FP_RISK",
        features=make_features(
            "TC_017",
            {
                "heat_input_mean": 4000.0,  # MARGINAL: 3800–4500
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="CONDITIONAL",
        notes="Cold weld by heat_input_mean but above RISK threshold. All LOF primary features GOOD.",
    ),
    EvalScenario(
        scenario_id="TC_018_voltage_cv_marginal",
        description="voltage_cv marginally elevated — arc length slightly unstable",
        category="FP_RISK",
        features=make_features(
            "TC_018",
            {
                "voltage_cv": 0.10,  # MARGINAL: 0.08–0.15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="CONDITIONAL",
        notes="voltage_cv maps to POROSITY not LOF/LOP. No RISK-band LOF features. Must stay CONDITIONAL.",
    ),
    EvalScenario(
        scenario_id="TC_019_arc_on_ratio_borderline",
        description="arc_on_ratio = 0.80 — borderline but in MARGINAL band",
        category="FP_RISK",
        features=make_features(
            "TC_019",
            {
                "arc_on_ratio": 0.80,  # MARGINAL: 0.75–0.90
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="CONDITIONAL",
        notes="arc_on_ratio MARGINAL — some restarts but not at RISK level. Must not trigger REWORK.",
    ),
    EvalScenario(
        scenario_id="TC_020_single_marginal_feature",
        description="One MARGINAL feature (heat_input_drop_severity), nothing in RISK",
        category="FP_RISK",
        features=make_features(
            "TC_020",
            {
                "heat_input_drop_severity": 12.0,  # MARGINAL: 10–15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="CONDITIONAL",
        notes="Single MARGINAL violation, no RISK. Core over-firing prevention test.",
    ),
    # ── FN_RISK (4) ───────────────────────────────────────────────────────────
    # Safety-critical. FNR = 0.00 requires all 4 to pass.
    # A miss here means a defective weld is accepted.
    EvalScenario(
        scenario_id="TC_021_thermal_spike_risk_floor",
        description="heat_diss_max_spike = 41.0 — minimum value inside RISK band",
        category="FN_RISK",
        features=make_features(
            "TC_021",
            {
                "heat_diss_max_spike": 41.0,  # RISK floor: > 40
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Floor case for thermal RISK band. A miss means the RISK threshold is not enforced.",
    ),
    EvalScenario(
        scenario_id="TC_022_angle_deviation_risk_floor",
        description="angle_deviation_mean = 15.1 — minimum value inside RISK band",
        category="FN_RISK",
        features=make_features(
            "TC_022",
            {
                "angle_deviation_mean": 15.1,  # RISK floor: > 15
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="Floor case for angle RISK band. Tests boundary precision on LOF geometry feature.",
    ),
    EvalScenario(
        scenario_id="TC_023_compound_marginal_risk",
        description="Two features at RISK from different domains — compound defect",
        category="FN_RISK",
        features=make_features(
            "TC_023",
            {
                "heat_input_drop_severity": 15.5,  # RISK: > 15 (LOF)
                "voltage_cv": 0.16,  # RISK: > 0.15 (POROSITY)
                "amps_cv": 0.13,  # RISK: > 0.12
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="heat_input_drop_severity in RISK triggers LOF override. Compound multi-domain RISK.",
    ),
    EvalScenario(
        scenario_id="TC_024_low_confidence_with_risk_feature",
        description="Low classifier confidence but one RISK LOF feature",
        category="FN_RISK",
        features=make_features(
            "TC_024",
            {
                "arc_on_ratio": 0.74,  # RISK: < 0.75 (LOF)
                "heat_input_mean": 4100.0,  # MARGINAL
                "heat_input_cv": 0.14,  # MARGINAL
            },
            quality_label="MARGINAL",
        ),
        expected_disposition="REWORK_REQUIRED",
        notes="arc_on_ratio RISK triggers LOF override regardless of classifier confidence. Most important FN scenario.",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def get_scenarios_by_category(category: str) -> list[EvalScenario]:
    return [s for s in SCENARIOS if s.category == category]


def get_scenario_by_id(scenario_id: str) -> Optional[EvalScenario]:
    for s in SCENARIOS:
        if s.scenario_id == scenario_id:
            return s
    return None


def print_scenario_summary() -> None:
    counts = {}
    for s in SCENARIOS:
        counts[s.category] = counts.get(s.category, 0) + 1
    print(f"EvalScenario summary: {len(SCENARIOS)} total")
    for cat, n in sorted(counts.items()):
        print(f"  {cat:<15} {n}")


if __name__ == "__main__":
    print_scenario_summary()
