"""
WarpSense -- Welding Standards Knowledge Base
backend/knowledge/build_welding_kb.py

Loads 63 structured chunks into ChromaDB covering:
  - AWS D1.1:2025  (Structural Welding Code)
  - ISO 5817:2023  (Quality levels B / C / D)
  - IACS Rec. 47 Rev.10 (Shipbuilding & Repair Quality Standards)
  - Heat input physics and parameter relationships
  - Root cause maps per defect type (LOF/LOP focus)
  - Corrective action protocols with specific parameter targets
  - Torch angle and travel speed effects

Usage:
    python build_welding_kb.py           # build and persist to ./chroma_db
    python build_welding_kb.py --test    # build + run smoke tests
"""

import argparse
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "welding_standards"
DEFAULT_EF = embedding_functions.DefaultEmbeddingFunction()

CHUNKS = [
    {"id": "aws_d11_scope", "text": "AWS D1.1/D1.1M:2025 Structural Welding Code governs welding requirements for carbon and low-alloy constructional steels. All welds shall be visually inspected unless otherwise specified. Visual inspection may begin after welds cool to ambient temperature.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 8 General", "chunk_type": "overview"}},
    {"id": "aws_d11_table81_fusion", "text": "AWS D1.1 Table 8.1 Item 2: There shall be complete fusion between weld and base metal. Incomplete penetration in CJP groove welds is not acceptable and shall be repaired. For CJP groove welds in cyclically loaded structures, zero incomplete penetration is tolerated. Incomplete penetration is a rejection criterion for all CJP welds.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 2", "defect_type": "incomplete_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_table81_undercut_static", "text": "AWS D1.1 Table 8.1 Item 7 Undercut Statically Loaded: For material less than 1 in thick, undercut shall not exceed 1/32 in. For material 1 in or greater, undercut shall not exceed 1/16 in for any weld.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_table81_undercut_cyclic", "text": "AWS D1.1 Table 8.1 Item 7 Undercut Cyclically Loaded: For primary members in tension transverse to tensile stress, undercut shall not exceed 0.01 in deep. This is the most stringent undercut limit. For all other cyclically loaded members, undercut shall not exceed 1/32 in.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_table81_porosity_static", "text": "AWS D1.1 Table 8.1 Item 8 Piping Porosity Statically Loaded: The sum of diameters of visible piping porosity 1/32 in or greater shall not exceed 3/8 in in any linear inch of weld. For welds less than 12 in, sum shall not exceed weld length times 0.06.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 8", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_table81_porosity_cyclic", "text": "AWS D1.1 Table 8.1 Item 8 Piping Porosity Cyclically Loaded: For cyclically loaded nontubular CJP groove welds transverse to tensile stress, zero porosity is permitted.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 8", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_lof_zero_tolerance", "text": "AWS D1.1 Incomplete Fusion Zero Tolerance: Incomplete fusion is defined as a condition where weld metal fails to fuse completely with base metal or adjacent weld beads. Under AWS D1.1, incomplete fusion is NOT accepted at any length. It is a direct rejection criterion requiring repair. This applies to VT, MT, PT, RT, and UT inspection. There is no acceptable length threshold for incomplete fusion.", "metadata": {"source": "AWS D1.1:2025", "section": "Clauses 8.9-8.13", "defect_type": "incomplete_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
    {"id": "aws_d11_heat_input_formula", "text": "AWS D1.1 Clause 6.8.5 Heat Input Formula: Heat Input kJ/in = (Voltage x Amperage x 60) / (1000 x Travel Speed in IPM). For SI: Heat Input kJ/mm = (Voltage x Amperage x 60) / (1000 x Travel Speed in mm/min). Heat input is an essential variable for WPS qualification when CVN/toughness requirements apply.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 6.8.5", "chunk_type": "formula"}},
    {"id": "aws_d11_short_circuit_ban", "text": "AWS D1.1 Short Circuit Transfer Prohibition: GMAW short-circuit transfer is NOT permitted for prequalified welding procedures under AWS D1.1 for structural welding. Short circuit transfer is susceptible to lack of fusion because the low arc energy is insufficient to melt sidewalls consistently. Spray transfer and pulsed spray are preferred.", "metadata": {"source": "AWS D1.1:2025", "section": "Prequalified WPS", "defect_type": "incomplete_fusion", "chunk_type": "procedure"}},
    {"id": "aws_d11_disposition_rework", "text": "AWS D1.1 Weld Repair and Disposition: Welds failing acceptance criteria shall be repaired or removed and replaced. Repair methods include gouging and re-welding for cracks and incomplete fusion, grinding for minor surface defects, additional passes for undersized welds. Repairs require a documented repair WPS and must be re-inspected using the same methods as the original weld.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 8.8", "chunk_type": "disposition"}},
    {"id": "aws_d11_wps_essential_variables", "text": "AWS D1.1 WPS Essential Variables: A Welding Procedure Specification must document current range, voltage range, travel speed range, preheat temperature, interpass temperature, electrode diameter, shielding gas composition and flow rate, and welding position. Changes beyond qualified ranges require re-qualification.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 5 WPS", "chunk_type": "procedure"}},
    {"id": "iso5817_overview", "text": "ISO 5817:2023 Quality Levels for Imperfections in Fusion-Welded Joints: Specifies quality levels for imperfections in fusion-welded joints in steel, nickel, titanium and their alloys. Three quality levels: B (highest strictest), C (intermediate), D (moderate lowest). Level B corresponds to highest structural integrity. ISO 5817 answers what is acceptable.", "metadata": {"source": "ISO 5817:2023", "section": "Scope", "chunk_type": "overview"}},
    {"id": "iso5817_level_selection", "text": "ISO 5817:2023 Quality Level Selection: Level B for fatigue-critical, safety-critical joints, marine primary structure. Level C for general structural welds, statically loaded with moderate consequence. Level D for non-critical brackets and fixtures. For shipyard structural hull welds, Level C or B is typical.", "metadata": {"source": "ISO 5817:2023", "section": "Section 4", "chunk_type": "guidance"}},
    {"id": "iso5817_lof_all_levels", "text": "ISO 5817:2023 Table 1 Lack of Fusion ref 401: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Not permitted. Lack of fusion is NEVER acceptable at any quality level under ISO 5817. This includes lack of side-wall fusion 4011, lack of inter-run fusion 4012, lack of root fusion 4013. LOF creates a planar discontinuity with catastrophic crack propagation risk.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.5", "defect_type": "lack_of_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_incomplete_root_penetration", "text": "ISO 5817:2023 Table 1 Incomplete Root Penetration ref 4021: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Short imperfections only h <= 0.2t but maximum 2 mm where t is plate thickness. Levels C and B: Not permitted at any length.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.6", "defect_type": "incomplete_penetration", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_lof_fillet_welds", "text": "ISO 5817:2023 Table 1 No.2.12 Lack of Fusion in Fillet Welds ref 401: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Short imperfections only h <= 0.4a but max 4 mm. LOF is zero-tolerance at B and C regardless of size because LOF is a planar defect with catastrophic crack propagation risk.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.2.12", "defect_type": "lack_of_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_undercut", "text": "ISO 5817:2023 Table 1 Undercut ref 5011: Level D t > 3 mm: h <= 0.2t max 1 mm. Level C t > 3 mm: h <= 0.1t max 0.5 mm. Level B t > 3 mm: h <= 0.05t max 0.5 mm. Undercut weakens section thickness at weld toe creating stress concentration for fatigue crack initiation.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_porosity_surface", "text": "ISO 5817:2023 Table 1 Surface Pore ref 2017: Level D: d <= 0.2s but max 2 mm. Level C: d <= 0.1s but max 1 mm. Level B: Not permitted. Porosity produces rounded volumetric defects rather than planar defects and is relatively less dangerous than LOF. Cluster porosity is not permitted at any level.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.3", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_cracks", "text": "ISO 5817:2023 Table 1 Cracks ref 100: Quality Level B Not permitted. Quality Level C Not permitted. Quality Level D Not permitted. All crack types are rejected at all quality levels. Types include longitudinal, transverse, crater, interface, and HAZ cracks.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.1", "defect_type": "crack", "severity": "reject", "chunk_type": "acceptance_criteria"}},
    {"id": "iso5817_systematic_imperfections", "text": "ISO 5817:2023 Section 5 Systematic Imperfections: Systematic imperfections are only permitted in quality level D. A systematic imperfection recurs repeatedly at regular intervals, suggesting a procedural or technique problem. A consistently high angle_deviation_mean or repeatedly low heat_input_min_rolling across sessions is a pattern of systematic imperfection requiring training correction.", "metadata": {"source": "ISO 5817:2023", "section": "Section 5", "chunk_type": "guidance"}},
    {"id": "iso5817_multiple_imperfections", "text": "ISO 5817:2023 Section 5 Multiple Imperfections: A welded joint should be assessed separately for each individual type of imperfection. When multiple imperfections are present simultaneously such as porosity plus undercut plus LOF, each must independently pass its quality level limit. The presence of porosity may mask underlying LOF.", "metadata": {"source": "ISO 5817:2023", "section": "Section 5", "chunk_type": "guidance"}},
    {"id": "iso5817_fatigue_annex_b", "text": "ISO 5817:2023 Annex B Fatigue Load Criteria: Additional requirements for welds subject to fatigue loading. At B125 highest fatigue demand: continuous undercut not permitted, weld toe radius r >= 4 mm for t >= 3 mm. Marine hull welding in cyclically loaded areas should reference Annex B criteria for primary structural members.", "metadata": {"source": "ISO 5817:2023", "section": "Annex B", "chunk_type": "fatigue"}},
    {"id": "iso6520_classification", "text": "ISO 6520-1:2007 Weld Imperfection Classification: Group 1 Cracks 100-series. Group 2 Cavities porosity piping 200-series. Group 3 Solid inclusions 300-series. Group 4 Incomplete fusion and penetration 400-series where 401 is LOF and 4021 is IRP. Group 5 Shape and dimension 500-series where 5011 is continuous undercut. Group 6 Miscellaneous 600-series.", "metadata": {"source": "ISO 6520-1:2007", "section": "All", "chunk_type": "overview"}},
    {"id": "iacs47_scope", "text": "IACS Recommendation 47 Rev.10 2021 Shipbuilding and Repair Quality Standard: Provides guidance on quality of hull structure during new construction and repair. Applies to primary and secondary structure. ANSI/AWS D1.1 is explicitly listed as a recognized international standard. Subcontractors must keep records of welder qualification certificates.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Scope", "chunk_type": "overview"}},
    {"id": "iacs47_high_heat_input_threshold", "text": "IACS UR W28 Rev.3 High Heat Input Thresholds: IACS defines high heat input welding as processes exceeding 50 kJ/cm for normal and higher strength hull structural steels. Above this threshold additional approval and testing is required. Typical target range for shipyard MIG welding on mild/HT steel is 1.0 to 3.0 kJ/mm. Heat inputs below 0.5 kJ/mm risk incomplete fusion.", "metadata": {"source": "IACS UR W28 Rev.3", "section": "High Heat Input", "chunk_type": "threshold", "defect_type": "lack_of_fusion"}},
    {"id": "iacs47_weld_ndt_coverage", "text": "IACS Rec 47 NDT Coverage: Current practice in shipyards involves spot NDT at typically 10% coverage. This means 90% of welds receive only visual inspection. LOF and LOP are subsurface planar defects invisible to visual inspection and often invisible to dye penetrant and magnetic particle unless they break the surface. Only UT reliably detects all orientations of LOF/LOP. AI-based sensor monitoring offers path to 100% first-pass LOF/LOP risk screening.", "metadata": {"source": "IACS Rec.47 / IACS UR W33", "section": "NDT", "chunk_type": "inspection", "defect_type": "lack_of_fusion"}},
    {"id": "iacs47_repair_disposition", "text": "IACS Rec 47 Repair Disposition: Defects are to be remedied by grinding and/or welding. Weld repairs require prior cleaning of groove, approved welding procedure, same or higher grade consumables, steel temperature not lower than 5 C, re-inspection by NDT after repair. For structural defects including LOF and LOP full gouge and re-weld is required.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Section 6", "chunk_type": "disposition"}},
    {"id": "iacs47_marine_environment_context", "text": "IACS Rec 47 Marine Welding Context: Shipyard welding occurs in demanding conditions including high humidity in coastal tropical locations, thick steel plates 10-50 mm, variable ambient temperatures, wind exposure affecting shielding gas. In Singapore and Southeast Asian shipyards high ambient humidity 80-90% RH increases hydrogen pickup risk. Pre-weld drying of consumables is mandatory.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Context", "chunk_type": "context"}},
    {"id": "iacs47_preheat", "text": "IACS Rec 47 Preheating: Minimum preheat of 50C is to be applied when ambient temperature is below 0C. For higher strength steels with Ceq > 0.43, preheat 100-175C depending on combined plate thickness. Moisture must be removed from weld area by heating torch before welding because moisture causes hydrogen-induced cracking.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Section 5", "chunk_type": "procedure"}},
    {"id": "heat_input_formula_physics", "text": "Heat Input Calculation Physics: Heat Input J/mm = (Voltage V x Current A x 60) / Travel Speed mm/min. Divide by 1000 for kJ/mm. Heat input governs penetration depth, HAZ width, cooling rate, microstructure, and toughness. Insufficient heat input causes incomplete fusion and cold lap. Excess heat input causes distortion, HAZ softening, and porosity from contaminant boiling.", "metadata": {"source": "AWS D1.1 / EN ISO 1011-1", "section": "Heat Input", "chunk_type": "formula"}},
    {"id": "heat_input_voltage_effect", "text": "Voltage Effect on Weld Quality: Voltage controls arc length and arc cone width. Higher voltage causes wider bead, flatter profile. Very high voltage causes undercut, inconsistent penetration, possible LOF at weld toes. For GMAW spray transfer on mild steel typical range is 22-28 V. Voltage instability with high CV indicates arc wandering and is a leading indicator of incomplete fusion and porosity risk. voltage_cv > 0.15 is a risk flag.", "metadata": {"source": "Technical reference", "section": "Voltage", "chunk_type": "parameter_effect", "defect_type": "incomplete_fusion"}},
    {"id": "heat_input_amperage_effect", "text": "Amperage Effect on Weld Quality: Amperage is the dominant driver of heat input. Higher amperage means deeper penetration and greater fusion. Too low amperage causes cold weld, lack of fusion, incomplete penetration. Amperage is directly correlated to wire feed speed in GMAW. amps_cv > 0.12 is a risk flag. Low amps_mean with high travel speed is the primary LOF/LOP sensor signature combination.", "metadata": {"source": "Technical reference", "section": "Amperage", "chunk_type": "parameter_effect", "defect_type": "incomplete_fusion"}},
    {"id": "heat_input_travel_speed_effect", "text": "Travel Speed Effect on Weld Quality: Travel speed is inversely proportional to heat input. Too fast cold travel causes insufficient heat to joint walls resulting in LOF, IRP, and poor tie-in. Too slow hot travel causes burn-through, distortion, and porosity. heat_input_drop_severity captures rapid cold transitions indicative of stitch restart events and travel speed spikes.", "metadata": {"source": "Technical reference", "section": "Travel Speed", "chunk_type": "parameter_effect", "defect_type": "lack_of_fusion"}},
    {"id": "heat_input_cv_significance", "text": "Coefficient of Variation CV in Welding: CV = standard deviation / mean. High CV on heat_input > 0.20 indicates unstable welding process where the welder is not maintaining consistent parameters. This leads to cold zones with LOF risk and hot zones with porosity risk alternating within a pass. heat_input_cv is a strong proxy for welder consistency even when mean heat input appears acceptable.", "metadata": {"source": "Technical reference", "section": "Process Stability", "chunk_type": "feature_explanation"}},
    {"id": "heat_dissipation_significance", "text": "Heat Dissipation Rate LOF Risk Signal: Spikes in heat dissipation rate indicate sudden torch movement causing rapid arc interruption, stitch starts and stops with cold restarts, excessive travel speed bursts, or loss of shielding gas coverage. Expert baseline: heat_diss_max_spike < 10 C/s. Novice risk threshold: heat_diss_max_spike > 40 C/s. Above 60 C/s high LOF/LOP risk REWORK likely required.", "metadata": {"source": "WarpSense technical basis", "section": "Feature Interpretation", "chunk_type": "feature_explanation", "defect_type": "lack_of_fusion"}},
    {"id": "root_cause_lof_primary", "text": "Root Causes Lack of Fusion: Primary causes are insufficient heat input where arc energy too low to melt sidewall metal, incorrect torch angle where arc directed away from fusion zone, excessive travel speed, short-circuit GMAW transfer, surface contamination, excessive wire extension, and cold restarts at stitch transitions. LOF is a planar defect invisible to X-ray if parallel to beam, visual inspection, and PT/MT.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "lack_of_fusion", "chunk_type": "root_cause"}},
    {"id": "root_cause_lop_primary", "text": "Root Causes Incomplete Root Penetration: Primary causes are insufficient amperage, excessive travel speed, root gap too small, root face too large, large electrode diameter for joint size, and incorrect torch angle in groove. LOP is most common in single-side CJP butt welds, narrow groove configurations, and positional welding. Low heat_input_mean combined with high angle_deviation = high LOP probability.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "incomplete_penetration", "chunk_type": "root_cause"}},
    {"id": "root_cause_porosity", "text": "Root Causes Porosity: Primary causes are moisture in flux or electrode coating, loss of shielding gas coverage from wind or excessive torch angle, base metal contamination, excessive travel speed, excessive voltage or long arc, and moisture-laden shielding gas. High heat_diss_max_spike at restart points combined with high voltage_cv increases porosity probability at stitch boundaries.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "porosity", "chunk_type": "root_cause"}},
    {"id": "root_cause_undercut", "text": "Root Causes Undercut: Primary causes are excessive amperage or voltage causing excess melting of base metal at weld toe, incorrect torch angle causing asymmetric heat distribution, excessive travel speed pulling molten metal from toe, and incorrect electrode manipulation. Corrective action: reduce amperage 10-15%, correct torch angle to 45 degrees, slow travel speed at weld toes.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "undercut", "chunk_type": "root_cause"}},
    {"id": "root_cause_cracking", "text": "Root Causes Weld Cracking: Hot cracking from high heat input and high dilution. Cold cracking from hydrogen-induced cracking in high carbon equivalent steel with high restraint and insufficient preheat. Crater cracking from abrupt arc termination. All cracks are zero tolerance at all AWS D1.1 and ISO 5817 levels. Extreme heat_input spikes followed by abrupt drops are a crater cracking risk signature.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "crack", "chunk_type": "root_cause"}},
    {"id": "torch_angle_work_angle", "text": "Torch Work Angle for T-joints and fillet welds: Standard optimal work angle is 45 degrees bisecting the joint to distribute heat equally to both members. Work angle too high > 55 degrees causes undercut on vertical member. Work angle too low < 35 degrees causes LOF on vertical leg. Maintaining +/- 5 degrees of target is professional standard. angle_deviation_mean > 10 degrees is elevated LOF risk. > 20 degrees is high LOF probability.", "metadata": {"source": "Technical reference", "section": "Torch Angle", "chunk_type": "technique", "defect_type": "lack_of_fusion"}},
    {"id": "torch_angle_variability_consequence", "text": "Torch Angle Variability Consequence: Welders often change torch angle to improve their view of the arc, which is a primary cause of varying penetration depth and lack of inter-run fusion. High angle_drift_1s indicates sudden technique breaks common at position changes and weld restarts. These are precisely the LOF risk points.", "metadata": {"source": "Technical synthesis", "section": "Torch Angle", "chunk_type": "feature_explanation", "defect_type": "lack_of_fusion"}},
    {"id": "corrective_lof_thermal_instability", "text": "Corrective Actions LOF from Thermal Instability: When heat_diss_max_spike > 40 C/s AND heat_input_cv > 0.20: Diagnosis is inconsistent travel speed with cold restart events. Action 1 maintain continuous arc without stops. Action 2 reduce travel speed variance by 20-30%. Action 3 verify wire feed speed is stable. Action 4 pre-heat restart points by dwelling 1-2 seconds before advancing. Expected: heat_diss_max_spike should drop below 20 C/s within 2 sessions if technique corrected.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
    {"id": "corrective_lof_angle_drift", "text": "Corrective Actions LOF from Torch Angle Deviation: When angle_deviation_mean > 15 degrees from 45 degree target: Diagnosis is misdirected arc with heat not reaching fusion zone. Action 1 return torch work angle to 45 +/- 5 degrees. Action 2 check body position since angle drift often caused by reaching or stretching. Action 3 use angle guide for repetitive welds. Action 4 practice on scrap coupons until angle_deviation < 10 degrees.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
    {"id": "corrective_lof_cold_window", "text": "Corrective Actions LOF from Cold Heat Windows: When heat_input_min_rolling < 3500 J AND heat_input_drop_severity > 15: Diagnosis is cold zones within pass at stitch transitions. Action 1 increase base amperage 10-15%. Action 2 at each stitch restart pause 1s before advancing. Action 3 check interpass temperature and preheat to minimum 50C if too cold. Action 4 ensure clean joint preparation. Safety constraint: do not increase heat input above 3.0 kJ/mm without re-qualifying WPS.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
    {"id": "corrective_undercut_high_heat", "text": "Corrective Actions Undercut from Excessive Heat: When heat_input_mean is high AND angle_deviation_mean > 10 degrees: Action 1 reduce amperage 10-15%. Action 2 correct torch work angle to 45 +/- 5 degrees. Action 3 slow travel speed at weld toes. Action 4 reduce weave width with toe dwell instead of wide sweep. For fatigue-critical Level B members verify undercut depth <= 0.05t per ISO 5817:2023 Annex B.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "undercut"}},
    {"id": "corrective_porosity_heat_diss", "text": "Corrective Actions Porosity from Arc Loss: When heat_diss_max_spike > 60 C/s: Action 1 check shielding gas flow rate set to 15-20 L/min and verify no leaks. Action 2 check for drafts and shield weld area. Action 3 reduce travel angle to maintain shielding gas coverage. Action 4 reduce voltage 1-2 V to shorten arc length. Action 5 pre-dry electrodes and wire since hydrogen from moisture is primary porosity cause in humid environments.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "porosity"}},
    {"id": "corrective_parameter_bounds", "text": "WarpSense Corrective Parameter Safety Bounds: All corrective adjustments must stay within WPS-qualified ranges. Amperage adjustments within +/-15% of WPS mid-range without re-qualification. Voltage within +/-10%. Travel speed within +/-30%. Torch angle target 45 +/- 10 degrees for fillet/T-joints. Heat input must not increase beyond WPS qualified maximum. If correction would exceed WPS bounds a new WPS must be qualified before implementing.", "metadata": {"source": "WarpSense system design", "section": "Safety Bounds", "chunk_type": "constraint"}},
    {"id": "warpsense_feature_thresholds", "text": "WarpSense Feature Threshold Reference: heat_diss_max_spike GOOD < 10 MARGINAL 10-40 RISK > 40 C/s. angle_deviation_mean GOOD < 8 MARGINAL 8-15 RISK > 15 degrees. heat_input_min_rolling GOOD > 4000 MARGINAL 3500-4000 RISK < 3500 J. heat_input_drop_severity GOOD < 10 MARGINAL 10-15 RISK > 15. heat_input_cv GOOD < 0.10 MARGINAL 0.10-0.20 RISK > 0.20. arc_on_ratio GOOD > 0.90 MARGINAL 0.75-0.90 RISK < 0.75.", "metadata": {"source": "WarpSense Phase 1", "section": "Thresholds", "chunk_type": "threshold"}},
    {"id": "warpsense_defect_feature_map", "text": "WarpSense Defect-to-Feature Mapping: LOF primary sensors are angle_deviation_mean, heat_input_min_rolling, heat_diss_max_spike, arc_on_ratio. LOP primary sensors are heat_input_mean, amps_cv, heat_input_cv. Porosity primary sensors are heat_diss_max_spike and voltage_cv. Undercut primary sensors are heat_input_mean high and angle_deviation_mean for asymmetric heat.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Agent Design", "chunk_type": "system_design"}},
    {"id": "warpsense_quality_class_mapping", "text": "WarpSense Quality Class to Standards Mapping: GOOD maps to ISO 5817 Level C or better and AWS D1.1 visual acceptance met. Disposition PASS. MARGINAL maps to ISO 5817 Level D and borderline AWS D1.1. Disposition CONDITIONAL PASS with monitoring. DEFECTIVE is below ISO 5817 Level D on LOF/LOP indicators. Disposition REWORK REQUIRED with UT inspection before acceptance.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Quality Classes", "chunk_type": "system_design"}},
    {"id": "warpsense_lof_lop_invisible_inspection", "text": "LOF/LOP Invisible Defect Problem: Lack of fusion and incomplete root penetration are the most dangerous weld defects because they are planar defects yet NOT detectable by visual inspection VT, dye penetrant PT, magnetic particle MT if planar to field, or X-ray RT if parallel to beam. Only UT reliably detects all orientations of LOF/LOP. Current shipyard NDT coverage is approximately 10% of welds. WarpSense provides 100% first-pass LOF/LOP risk screening.", "metadata": {"source": "WarpSense system rationale", "section": "Business case", "defect_type": "lack_of_fusion", "chunk_type": "context"}},
    {"id": "warpsense_heat_input_expert_novice", "text": "WarpSense Expert vs Novice Benchmark Phase 1: heat_diss_max_spike Expert 3.6 vs Novice 65.2 C/s 18x separation. angle_deviation_mean Expert 4.0 vs Novice 20.7 degrees 5x separation. heat_input_min_rolling Expert 3982 vs Novice 3211 J 24% drop cold windows. heat_diss_max_spike ranked #1 feature by both GradientBoosting and XGBoost independently.", "metadata": {"source": "WarpSense Phase 1 results", "section": "Benchmarks", "chunk_type": "benchmark"}},
    {"id": "warpsense_arc_on_ratio", "text": "WarpSense Arc-On Ratio Feature: arc_on_ratio is fraction of session frames where arc is active V > 5 and A > 5. Low arc_on_ratio < 0.75 indicates frequent arc interruptions. Each arc restart is a LOF risk point cold restart interface. Expert arc_on_ratio is typically 0.90-0.95. Novice can drop to 0.60-0.70 with frequent stops for repositioning.", "metadata": {"source": "WarpSense Phase 1", "section": "Feature Explanation", "chunk_type": "feature_explanation"}},
    {"id": "research_amirafshari_2022", "text": "Research Anchor Amirafshari and Kolios 2022 International Journal of Fatigue: LOF and LOP are the dominant fatigue-critical defects in shipyard welds yet systematically missed by conventional inspection regimes including VT, PT, and RT. The paper quantifies the gap between true defect occurrence and detected defect rates at typical 10% NDT coverage. Travel speed instability and torch angle variability are the dominant controllable causal factors for LOF in production welding.", "metadata": {"source": "Amirafshari & Kolios 2022, Int. J. Fatigue", "section": "Research basis", "chunk_type": "research"}},
    {"id": "stitch_welding_risk", "text": "Stitch Welding Risk LOF at Restart Interfaces: Each restart creates a cold interface. The first 2-5 mm of each restart is at elevated LOF/LOP risk. Novice sensor signature is high heat_input_drop_severity and high heat_diss_max_spike. Mitigation: pre-heat restart crater before advancing, use short overlap at each restart advancing torch back 5 mm into previous bead, inspect stitch start points specifically in NDT.", "metadata": {"source": "Technical synthesis", "section": "Stitch Welding", "chunk_type": "technique", "defect_type": "lack_of_fusion"}},
    {"id": "humidity_tropical_context", "text": "Tropical Shipyard Context Humidity and Hydrogen: Singapore and Southeast Asian shipyards operate at 80-90% relative humidity. Flux-coated SMAW electrodes must be baked at 300C for 2 hours and stored at 120C. Hydrogen from moisture is the primary porosity cause and contributes to hydrogen-induced cold cracking in higher strength steels. Rapid heat dissipation in tropical humidity compresses the temperature window for hydrogen outgassing.", "metadata": {"source": "IACS Rec.47 + Technical synthesis", "section": "Environment", "chunk_type": "context"}},
    {"id": "ndt_method_selection", "text": "NDT Method Selection for LOF/LOP per ISO 17635: For LOF planar subsurface use UT PAUT preferred which detects LOF in all orientations, RT which detects LOF only if beam perpendicular to defect plane, or TOFD highly sensitive for planar defects. WarpSense recommendation: when AI risk score indicates HIGH LOF/LOP probability require UT inspection of flagged segments before acceptance. Targeted UT replaces random 10% coverage with risk-stratified coverage.", "metadata": {"source": "ISO 17635", "section": "NDT Selection", "chunk_type": "inspection", "defect_type": "lack_of_fusion"}},
    {"id": "disposition_framework", "text": "WarpSense Disposition Framework: PASS all features in GOOD range confidence > 0.80 ISO 5817 Level C met. Standard documentation next inspection at normal schedule. CONDITIONAL one or more features in MARGINAL band or confidence 0.60-0.80. Increase monitoring for next 3 sessions and flag for supervisor review. REWORK REQUIRED any LOF/LOP feature in RISK range or confidence > 0.75 for DEFECTIVE. Stop acceptance, require UT inspection, issue corrective action sheet. Third consecutive REWORK for same welder triggers mandatory retraining.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Disposition", "chunk_type": "disposition"}},
    {"id": "continuous_novice_signature", "text": "Continuous Novice Weld Sensor Signature: High arc_on_ratio 0.85-0.95 continuous arc few stops. High angle_deviation_mean > 15 degrees poor torch discipline. High heat_diss_max_spike > 40 C/s technique corrections causing momentary speed bursts. Moderate heat_input_cv 0.15-0.25 inconsistent parameter control. Low heat_input_min_rolling < 3500 J despite adequate mean from travel speed bursts. This pattern is more dangerous than stitch welding because LOF is distributed throughout the weld length.", "metadata": {"source": "WarpSense Phase 1 analysis", "section": "Pattern Recognition", "chunk_type": "benchmark"}},
    {"id": "expert_weld_signature", "text": "Expert Weld Target Sensor Pattern: heat_diss_max_spike < 5 C/s controlled restarts. angle_deviation_mean < 5 degrees from 45 degree target. heat_input_min_rolling > 4000 J no cold windows. heat_input_cv < 0.08 highly consistent process. voltage_cv < 0.06 and amps_cv < 0.06 stable arc. arc_on_ratio 0.88-0.92. heat_input_drop_severity < 10 managed stitch transitions. Expert signature is the target state WarpSense corrective actions aim to achieve.", "metadata": {"source": "WarpSense Phase 1 analysis", "section": "Pattern Recognition", "chunk_type": "benchmark"}},
    {"id": "multi_pass_interpass_temp", "text": "Multi-Pass Welding Interpass Temperature: Too cold below minimum preheat causes LOF at inter-run interfaces. Too hot above maximum interpass causes HAZ softening in TMCP steels and increased distortion. Typical maximum interpass temperature for shipyard hull steel is 250C. Very low heat_diss_mean may indicate welding is occurring on a very hot base suggesting too high interpass temperature. Very high heat_diss_mean indicates cold interpass and LOF risk.", "metadata": {"source": "AWS D1.1 / IACS Rec.47", "section": "Multi-pass", "chunk_type": "procedure"}},
    {"id": "iso15614_wps_qualification", "text": "ISO 15614-1 WPS Qualification: Specifies requirements for qualification of welding procedures by testing. PQR documents actual test conditions. WPS defines production welding parameters. Parameters documented include base material, filler metal, position, heat input range, preheat, interpass temperature. WarpSense features map directly to WPS essential variables providing real-time monitoring of whether production welding stays within qualified parameter envelopes.", "metadata": {"source": "ISO 15614-1", "section": "WPS Qualification", "chunk_type": "procedure"}},
]


SMOKE_TESTS = [
    {"name": "LOF acceptance criteria", "query": "Is lack of fusion acceptable in ISO 5817 quality level C welds?", "expect_id": "iso5817_lof_all_levels"},
    {"name": "Heat dissipation spike corrective", "query": "heat_diss_max_spike is 65 degrees per second corrective action", "expect_id": "corrective_lof_thermal_instability"},
    {"name": "Torch angle LOF root cause", "query": "angle deviation from 45 degrees causing incomplete fusion risk", "expect_id": "torch_angle_work_angle"},
    {"name": "Marine shipyard NDT gap", "query": "shipyard weld inspection coverage LOF invisible to X-ray visual", "expect_id": "warpsense_lof_lop_invisible_inspection"},
    {"name": "AWS LOF zero tolerance", "query": "AWS D1.1 incomplete fusion acceptance criteria rejection", "expect_id": "aws_d11_lof_zero_tolerance"},
]


def kb_is_ready() -> bool:
    """
    Return True if the persisted collection exists and has the expected chunk count.
    Used by init_system to skip rebuild when chroma_data volume already has valid index.
    """
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        coll = client.get_collection(COLLECTION_NAME)
        return coll.count() == len(CHUNKS)
    except Exception:
        return False


def build_knowledge_base(persist=True, verbose=True):
    if persist:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    else:
        client = chromadb.EphemeralClient()
    try:
        client.delete_collection(COLLECTION_NAME)
        if verbose:
            print(f"[KB] Deleted existing collection")
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=DEFAULT_EF,
        metadata={"hnsw:space": "cosine"},
    )
    ids = [c["id"] for c in CHUNKS]
    texts = [c["text"] for c in CHUNKS]
    metadatas = [c["metadata"] for c in CHUNKS]
    batch_size = 50
    for i in range(0, len(CHUNKS), batch_size):
        collection.add(
            ids=ids[i:i + batch_size],
            documents=texts[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )
        if verbose:
            print(f"[KB] Loaded {min(i + batch_size, len(CHUNKS))}/{len(CHUNKS)} chunks...")
    if verbose:
        print(f"[KB] Built: {collection.count()} chunks in {COLLECTION_NAME!r}")
        if persist:
            print(f"[KB] Persisted to: {CHROMA_PATH}")
    return collection


def query_kb(collection, query, n_results=5, filter_defect=None):
    where = {"defect_type": filter_defect} if filter_defect else None
    results = collection.query(
        query_texts=[query], n_results=n_results, where=where,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for i, doc in enumerate(results["documents"][0]):
        output.append({
            "id": results["ids"][0][i],
            "text": doc,
            "source": results["metadatas"][0][i].get("source", "unknown"),
            "section": results["metadatas"][0][i].get("section", ""),
            "score": round(1 - results["distances"][0][i], 4),
        })
    return output


def run_smoke_tests(collection):
    print("\\n" + "=" * 60)
    print("SMOKE TESTS")
    print("=" * 60)
    passed = 0
    for test in SMOKE_TESTS:
        results = query_kb(collection, test["query"], n_results=3)
        top_ids = [r["id"] for r in results]
        hit = test["expect_id"] in top_ids
        status = "PASS" if hit else "FAIL"
        if hit:
            passed += 1
        test_name = test["name"]
        query_preview = test["query"][:80]
        expect_id = test["expect_id"]
        print(f"\\n{status} -- {test_name}")
        print(f"  Query: {query_preview}")
        print(f"  Expected: {expect_id}")
        print(f"  Top-3: {top_ids}")
    print(f"\\nResults: {passed}/{len(SMOKE_TESTS)} passed")
    return passed == len(SMOKE_TESTS)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--ephemeral", action="store_true")
    args = parser.parse_args()
    print(f"WarpSense KB Builder -- {len(CHUNKS)} chunks")
    collection = build_knowledge_base(persist=not args.ephemeral, verbose=True)
    if args.test:
        run_smoke_tests(collection)
