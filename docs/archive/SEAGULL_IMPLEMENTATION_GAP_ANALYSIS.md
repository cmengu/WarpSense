# Seagull Pilot Implementation — Gap Analysis

**Purpose:** Compare the Seagull pilot architecture (WelderReport, team dashboard, AI feedback) against the current Shipyard Welding MVP codebase.

---

## TL;DR

| Layer | Seagull Spec | Current State | Status |
|-------|--------------|---------------|--------|
| **`app/seagull/`** | Team dashboard + WelderReport | **Does not exist** | ❌ Not implemented |
| **`lib/ai-feedback.ts`** | Rule-based AI engine | **Does not exist** | ❌ Not implemented |
| **`lib/mock-data.ts`** | Client-side generate_expert/novice | **Backend only** (Python) | ⚠️ Data exists, wrong layer |
| **`HeatMap`** | Side-by-side thermal comparison | ✅ Exists, used on compare page | ✅ Implemented |
| **`FeedbackPanel`** | AI advice display | **Does not exist** | ❌ Not implemented |
| **`TrendChart`** | Progress over time | **Does not exist** | ❌ Not implemented |
| **`ComparisonView`** | Side-by-side wrapper | Compare page does inline | ⚠️ Partial (no reusable component) |

---

## Part 1: Routing & Pages

### Seagull Spec

```
/app/seagull/
  ├── page.tsx                  [Team Dashboard — 3 mock welders, score cards]
  └── welder/[id]/page.tsx      [Individual Report — Mike Chen, AI feedback]
```

### Current State

| Route | Exists | Notes |
|-------|--------|-------|
| `/app/seagull/page.tsx` | ❌ No | No Seagull routes at all |
| `/app/seagull/welder/[id]/page.tsx` | ❌ No | Would be `app/seagull/welder/[id]/page.tsx` |
| `/app/page.tsx` | ✅ | Dashboard — but generic (MetricCard, LineChart), not Seagull team overview |
| `/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | ✅ | Side-by-side comparison (heatmaps + delta), session IDs |
| `/app/replay/[sessionId]/page.tsx` | ✅ | Single-session replay, HeatMap + TorchViz3D + ScorePanel |

**Gap:** All Seagull pages (`/seagull`, `/seagull/welder/[id]`) are missing.

---

## Part 2: Data Flow

### Seagull Spec (Client-side mock for demo)

- **Mock Data Files (lib/mock-data.ts):**
  - `generate_expert_session()` → Session (1500 frames)
  - `generate_novice_session()` → Session (1200 frames)
  - `generate_improving_session()` → Session (1400 frames)

- **AI Feedback Engine (lib/ai-feedback.ts):**
  - `detectPatterns()` → WeldPattern[]
  - `assessWelder()` → WelderProfile
  - `generateFeedback()` → string (personalized)
  - `generateAIFeedback()` → AIFeedbackResult

- **Processing:** All in browser, no backend calls for pilot demo.

### Current State

| Component | Exists | Location | Notes |
|-----------|--------|----------|-------|
| `generate_expert_session` | ✅ | `backend/data/mock_sessions.py` | Python, server-side |
| `generate_novice_session` | ✅ | `backend/data/mock_sessions.py` | Python, server-side |
| `generate_improving_session` | ❌ | — | Not in backend |
| `lib/mock-data.ts` | ❌ | — | Frontend has no client-side mock sessions |
| `lib/ai-feedback.ts` | ❌ | — | No AI feedback engine |
| `AIFeedbackResult`, `WelderProfile`, `WeldPattern` | ❌ | — | Types not defined |
| `fetchSession` | ✅ | `lib/api.ts` | Fetches from backend |
| `fetchScore` | ✅ | `lib/api.ts` | Rule-based score (5 rules), not AI feedback |

**Gap:**

1. **Seagull expects client-side mock data** — Current system uses backend API (`fetchSession`, `fetchScore`). For offline demo you'd need either:
   - A frontend `mock-data.ts` that returns Session-shaped objects (or fetches from a mock API), or
   - Seed the DB and hit real endpoints (requires backend + network).

2. **No AI feedback engine** — Backend has rule-based scoring (`SessionScore` with 5 rules), not `generateAIFeedback()` with `summary`, `feedback_items`, `skill_level`, `trend`.

3. **No `generate_improving_session`** — Backend only has expert, novice, and large.

---

## Part 3: Components

### Seagull Spec

| Component | Purpose |
|-----------|---------|
| `SeagullDashboard` | Team overview: 3 welders, score cards, trend indicators |
| `WelderReport` | Individual: score header, AI summary, side-by-side heatmaps, feedback items, trend chart |
| `HeatMap` | Thermal visualization |
| `FeedbackPanel` | AI-generated advice display |
| `TrendChart` | Progress over time (LineChart with historical scores) |
| `ComparisonView` | Side-by-side heatmap wrapper |

### Current State

| Component | Exists | File | Used By |
|-----------|--------|------|---------|
| `HeatMap` | ✅ | `components/welding/HeatMap.tsx` | replay, compare |
| `ScorePanel` | ✅ | `components/welding/ScorePanel.tsx` | replay (shows rule-based score) |
| `TorchAngleGraph` | ✅ | `components/welding/TorchAngleGraph.tsx` | replay |
| `TorchViz3D` | ✅ | `components/welding/TorchViz3D.tsx` | replay, dev/torch-viz |
| `FeedbackPanel` | ❌ | — | — |
| `TrendChart` | ❌ | — | — |
| `ComparisonView` | ❌ | — | Compare page does inline grid |
| `SeagullDashboard` | ❌ | — | — |
| `WelderReport` | ❌ | — | — |

**Gap:** `FeedbackPanel`, `TrendChart`, `ComparisonView`, `SeagullDashboard`, and `WelderReport` are not implemented.

---

## Part 4: WelderReport Page — Detailed Mapping

### Seagull WelderReport (from spec)

```tsx
// app/seagull/welder/[id]/page.tsx
- useState: report (AIFeedbackResult), session, expertSession
- useEffect: generate_novice_session(), generate_expert_session(), generateAIFeedback()
- Score Header: report.score, report.skill_level, report.trend
- AI Summary: report.summary
- Side-by-side Heatmaps: Expert vs Your Weld (extractHeatmapData)
- Feedback Items: report.feedback_items.map(FeedbackItem)
- Trend Chart: historicalScores
- Export: Email Report, Download PDF
```

### Closest Current Equivalent: Compare Page

| WelderReport Feature | Compare Page | Replay Page | Notes |
|----------------------|--------------|-------------|-------|
| Side-by-side heatmaps | ✅ Yes | ❌ No (single session) | Compare has Session A vs B |
| extractHeatmapData | ✅ Yes | ✅ Yes | Both use it |
| Score display | ❌ No | ✅ ScorePanel | Replay shows rule-based score |
| AI summary | ❌ | ❌ | Neither has AI feedback |
| Feedback items | ❌ | ❌ | Neither |
| Trend chart | ❌ | ❌ | Neither |
| Export buttons | ❌ | ❌ | Neither |
| Welder name / report title | ❌ | ❌ | Compare uses session IDs |
| Mock data in useEffect | ❌ | ❌ | Both use fetchSession (API) |

**Gap:** Compare page has the side-by-side heatmap pattern but lacks AI feedback, trend chart, report framing (welder name, date), and export. Replay has scoring but no comparison. Neither is a WelderReport.

---

## Part 5: Summary — What Exists vs What's Missing

### ✅ Already Implemented (Reusable)

| Item | Location |
|------|----------|
| `HeatMap` | `components/welding/HeatMap.tsx` |
| `extractHeatmapData` | `utils/heatmapData.ts` |
| `Session` type | `types/session.ts` |
| `fetchSession`, `fetchScore` | `lib/api.ts` |
| Side-by-side heatmap layout | `compare/[sessionIdA]/[sessionIdB]/page.tsx` |
| `ScorePanel` (rule-based) | `components/welding/ScorePanel.tsx` |
| `generate_expert_session`, `generate_novice_session` | `backend/data/mock_sessions.py` |

### ❌ Not Implemented

| Item | Needed For |
|------|------------|
| `app/seagull/page.tsx` | Team dashboard |
| `app/seagull/welder/[id]/page.tsx` | WelderReport |
| `lib/ai-feedback.ts` | AI engine (generateAIFeedback, detectPatterns, etc.) |
| `lib/mock-data.ts` | Client-side demo (or adapter to backend) |
| `generate_improving_session` | Improving welder demo |
| `FeedbackPanel` | AI advice display |
| `FeedbackItem` | Single feedback row |
| `TrendChart` | Progress over time |
| `AIFeedbackResult`, `WelderProfile`, `WeldPattern` types | AI feedback contract |
| Export (Email, PDF) buttons | Report export |

### ⚠️ Partial / Different Layer

| Item | Current | Seagull Expects |
|------|---------|-----------------|
| Mock sessions | Backend Python | Frontend `lib/mock-data.ts` |
| Score | Rule-based (5 rules) | AI feedback (summary, items, skill_level) |
| Dashboard | Generic metrics/charts | Seagull team overview (3 welders) |

---

## Part 6: Implementation Effort Estimate

| Task | Effort | Depends On |
|------|--------|------------|
| Add `lib/ai-feedback.ts` (rule-based engine) | Medium | Session type, pattern detection logic |
| Add `lib/mock-data.ts` (fetch from seeded API or client mock) | Small–Medium | Backend sessions or JSON fixtures |
| Add `app/seagull/page.tsx` (team dashboard) | Medium | ai-feedback, mock-data |
| Add `app/seagull/welder/[id]/page.tsx` (WelderReport) | Medium | ai-feedback, HeatMap, new components |
| Add `FeedbackPanel` / `FeedbackItem` | Small | AIFeedbackResult type |
| Add `TrendChart` | Small | Historical scores (mock or API) |
| Add Export buttons (stub) | Small | — |
| Add `generate_improving_session` (backend) | Small | mock_sessions.py |

---

## Part 7: Recommended Approach

1. **Create `lib/ai-feedback.ts`** — Rule-based `generateAIFeedback(session, historical)` returning `AIFeedbackResult`. Use existing backend `Session`/`Frame` shape.
2. **Create `lib/mock-data.ts`** — Either:
   - Call `fetchSession` for `sess_expert_001` and `sess_novice_001` (requires backend), or
   - Add minimal client-side Session fixtures for offline demo.
3. **Create `app/seagull/welder/[id]/page.tsx`** — WelderReport using HeatMap (reuse), new FeedbackPanel, TrendChart, export stubs.
4. **Create `app/seagull/page.tsx`** — Team dashboard with 3 welder cards.
5. **Add `generate_improving_session`** to backend if you need three distinct profiles.

---

## Reference Files

- Compare page (side-by-side heatmaps): `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`
- Replay page (single session + score): `my-app/src/app/replay/[sessionId]/page.tsx`
- HeatMap: `my-app/src/components/welding/HeatMap.tsx`
- heatmapData: `my-app/src/utils/heatmapData.ts`
- API: `my-app/src/lib/api.ts`
- Backend mock sessions: `backend/data/mock_sessions.py`
