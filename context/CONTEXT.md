# Shipyard Welding MVP — Context

> **Purpose:** Canonical list of implemented features for AI reference.  
> **Last Updated:** 2026-02-24

---

## Implemented Features

### Warp Prediction ML
**Status:** ✅
**What:** ONNX-based logistic regression; 50-frame rolling window → warp probability + RiskLevel
**Location:** `backend/services/prediction_service.py`, `backend/routes/predictions.py`, `backend/models/warp_model.onnx`
**Frontend:** `WarpRiskGauge.tsx`

### AI Narrative Engine
**Status:** ✅
**What:** Anthropic-powered 3-paragraph coaching report, cached in `session_narratives` table
**Location:** `backend/services/narrative_service.py`, `backend/routes/narratives.py`
**Frontend:** `NarrativePanel.tsx`

### Longitudinal Skill Trajectory
**Status:** ✅
**What:** Per-welder chronological score history, trend slope, projected next score
**Location:** `backend/services/trajectory_service.py`; route in `welders.py`
**Frontend:** `TrajectoryChart.tsx`

### Defect Pattern Library
**Status:** ✅
**What:** Session-scoped annotations + cross-session defect library with deep-links to replay
**Location:** `backend/routes/annotations.py`, `backend/models/annotation.py`
**Frontend:** `AnnotationMarker.tsx`, `AddAnnotationPanel.tsx`, `/defects` page

### Comparative Benchmarking
**Status:** ✅
**What:** Per-metric percentile rankings vs all welders; supervisor Rankings tab
**Location:** `backend/services/benchmark_service.py`; route in `welders.py`
**Frontend:** `BenchmarkPanel.tsx`, `RankingsTable.tsx`

### Automated Coaching Protocol
**Status:** ✅
**What:** 12 seeded drills; auto-assignment based on benchmark; progress tracking
**Location:** `backend/services/coaching_service.py`; routes in `welders.py`
**Frontend:** `CoachingPlanPanel.tsx`
**Hook:** Auto-assign triggered in GET /score when total < 60

### Operator Credentialing
**Status:** ✅
**What:** 3 cert standards (AWS D1.1, ISO 9606, Internal Basic); session-based readiness evaluation
**Location:** `backend/services/cert_service.py`; route in `welders.py`
**Frontend:** `CertificationCard.tsx`

### Multi-Site Org Hierarchy
**Status:** ✅
**What:** sites + teams tables; nullable team_id on sessions; aggregate filter params
**Location:** `backend/routes/sites.py`, `backend/models/site.py`
**Frontend:** `SiteSelector.tsx` in supervisor page

### iPad Companion PWA
**Status:** ✅
**What:** `/live` page; polling warp-risk; 2D angle indicator; no WebGL; PWA manifest
**Location:** `app/(app)/live/page.tsx`, `LiveAngleIndicator.tsx`, `LiveStatusLED.tsx`
