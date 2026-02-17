# [Feature] WarpSense Micro-Feedback: Real-Time Frame-Level Guidance for Welding Quality

**Time Budget:** 30-45 minutes MINIMUM for comprehensive issue capture.  
**Status:** Open  
**Created:** 2025-02-17

---

## Phase 0: Understand the Workflow Position

**This is Step 1 of 3:**
1. **Create Issue** ← This document (capture the WHAT and WHY)
2. **Explore Feature** (deep dive into HOW)
3. **Create Plan** (step-by-step implementation)

---

## MANDATORY PRE-ISSUE THINKING SESSION

### A. Brain Dump (5 minutes minimum)

**Raw thinking:**

The MVP currently gives welders a session-level score (0–100) and rule-based feedback like "Current fluctuated by 5.2A — aim for stability under 3A" or "Angle deviation 12.1° — keep within ±5°". But that's AFTER the weld is done. A welder replaying their session sees heatmaps, 3D torch, angle graph — but no guidance pointing to specific moments. "You messed up at frame 4200" is more actionable than "Your overall angle consistency was bad." What we're missing: frame-level, time-anchored micro-feedback that says "here, at this instant, your torch angle drifted" or "here, your thermal asymmetry spiked." 

Why does this matter? Training. QA. Replay becomes a learning tool instead of just a playback. Welders can scrub to the bad moment, see exactly what went wrong, and internalize the correction. The feature plan calls this "converting passive session replay into proactive, per-frame guidance." 

What prompted this: the existing scoring engine computes session-level aggregates (amps_stddev, angle_max_deviation, north_south_delta_avg, etc.). We never exposed WHERE in the session the problems occurred. The Frame model already has volts, amps, angle_degrees, thermal_snapshots at 100Hz (10ms). We have extractFivePointFromFrame, extractHeatDissipation, getFrameAtTimestamp. The data exists — we're just not surfacing frame-level insights.

Assumptions: (1) Welders want per-frame feedback, not just session summary. (2) Moving-average / deviation thresholds can be tuned without ML. (3) Batch precomputation for 10k+ frames is feasible — we shouldn't compute on scrub. (4) FeedbackPanel can be extended to show frame-indexed items, and the replay timeline can show colored markers. (5) TorchViz3D and HeatmapPlate3D could optionally highlight deviations visually.

What could go wrong? Threshold fatigue — too many alerts. Performance — 50k frames × multiple generators could be slow. UX overload — wall of feedback items. We need severity levels (info/warning/critical) and possibly aggregation ("3 angle drift events in first 30s"). 

What don't we know? Optimal thresholds per weld type. Whether pilot yards want configurable thresholds. Whether we need an API to persist micro-feedback or compute on-the-fly. Cooling-rate detection specifics — heat_dissipation is per-frame but "abnormal" needs definition.

Simplest version: Torch Angle Drift + Thermal Symmetry only, no overlays, FeedbackPanel with frame links. Complete version: angle, speed, thermal, cooling, voltage; Replay Timeline markers; optional 3D overlays; session summary; exportable reports.

Who's affected: All welders using replay/demo; QA evaluators; trainers. Urgency: Medium — differentiator for training/QA use case; not blocking core MVP.

### B. Question Storm (20+ questions)

1. What triggers micro-feedback generation? (Session load? On-demand?)
2. When does computation run — client or server?
3. Who sees micro-feedback? (Replay page, WelderReport, both?)
4. How often do sessions exceed 10k frames?
5. What's the impact if we don't build this?
6. What's the impact if we do?
7. Are we assuming welders will act on alerts?
8. Are we assuming thresholds are universal or per-weld-type?
9. What similar issues exist? (Seagull pilot expansion added session-level AI feedback)
10. What did we learn from Seagull? (FeedbackItem pattern, RULE_TEMPLATES)
11. How do we map frame index to timestamp for timeline markers?
12. Do we need "critical" severity or is info/warning enough?
13. What's the moving average window for voltage/amperage? (Plan says 10–50 frames)
14. How do we define "target speed" for weld travel?
15. What thermal variance threshold triggers asymmetry alert? (Plan: >20°C)
16. How is cooling rate "abnormal" defined?
17. Can FeedbackPanel scroll to / highlight item when user scrubs to that frame?
18. Does TorchViz3D support visual deviation overlay?
19. How many feedback items is too many for a session?
20. Do we persist micro-feedback or recompute each time?
21. What's the export format for QA reports?
22. How do we handle frames with null volts/amps/angle?

### C. Five Whys Analysis

**Problem:** Welders get session-level feedback but not frame-level guidance during replay.

**Why #1:** Why is this a problem? — Welders can't pinpoint which moments caused poor quality.

**Why #2:** Why is that a problem? — They replay the whole session hoping to notice something; inefficient learning.

**Why #3:** Why is that a problem? — Training time increases; welders don't improve as fast as they could.

**Why #4:** Why is that a problem? — Pilot yards want faster skill uptake and lower rework.

**Why #5:** Why is that the real problem? — Replay is passive; we need to make it actively teach by surfacing per-frame deviations.

**Root cause identified:** Lack of frame-level, time-anchored actionable feedback during replay.

---

## Required Information Gathering

### 1. Understand the Request

**User's initial request (from task description):**  
Enhance the MVP to provide real-time, frame-level actionable guidance for welders by detecting deviations in angle, thermal patterns, electrical stability, and welding dynamics — improving quality and reducing rework.

**Core features requested:**
- Torch Angle Drift Alerts (e.g. "Torch angle drifted 12° at frame 4200 — keep within 5°")
- Weld Speed Feedback (±20% from target)
- Thermal Symmetry Alerts (N/S/E/W/center variance >20°C)
- Cooling Rate Feedback
- Voltage/Amperage Alerts (spikes/dips vs moving average)
- Unified Feedback Architecture (FeedbackItem model with frameIndex, type, severity)
- Integration: FeedbackPanel, Replay Timeline markers, optional TorchViz3D/HeatmapPlate3D overlays

**Clarifications obtained:**  
- Phased rollout: Phase 1 (angle + thermal), Phase 2 (electrical + speed), Phase 3 (cooling + summary), Phase 4 (tune thresholds).  
- Configurable thresholds per weld type or skill level mentioned.  
- Batch precomputation for >10k frames.  
- SSR-safe dynamic imports for 3D.

**Remaining ambiguities:**  
- Exact threshold values per weld type.  
- Whether "target speed" comes from expert session or config.  
- Persistence vs recompute strategy.

### 2. Search for Context

#### Codebase Search — Documented Findings

**Similar existing features:**

1. **Feature:** `FeedbackPanel` at `my-app/src/components/welding/FeedbackPanel.tsx`
   - **What it does:** Renders `FeedbackItem[]` with severity styling (info=blue, warning=violet).
   - **Relevant patterns:** Uses `FeedbackItem` from `@/types/ai-feedback`; supports `severity`, `message`, `suggestion`.
   - **What we can reuse:** Component structure; extend for `frameIndex` and `type`; add "critical" severity styling.
   - **What we should avoid:** Current FeedbackItem has no `frameIndex` or `type` — session-level only.

2. **Feature:** `generateAIFeedback` at `my-app/src/lib/ai-feedback.ts`
   - **What it does:** Maps `SessionScore.rules` to human-readable `FeedbackItem[]`; uses `RULE_TEMPLATES` for amps_stability, angle_consistency, thermal_symmetry, etc.
   - **Relevant patterns:** Pure function; deterministic; template-based messages.
   - **What we can reuse:** Template pattern; extend or create parallel `generateMicroFeedback(frames)`.
   - **What we should avoid:** Session-level only; no frame index; `timestamp_ms: null` on all items.

3. **Feature:** `extract_features` at `backend/features/extractor.py`
   - **What it does:** Computes session aggregates: amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range.
   - **Relevant patterns:** Backend-side; stateless; uses Frame.volts, Frame.amps, Frame.angle_degrees, thermal_snapshots.
   - **What we can reuse:** Logic patterns; could add frame-level extractors or run per-frame in a micro-feedback backend.
   - **What we should avoid:** Session-only output — we need per-frame or per-deviation output.

4. **Feature:** `extractFivePointFromFrame` at `my-app/src/utils/frameUtils.ts`
   - **What it does:** Returns { center, north, south, east, west } temps from thermal_snapshots[0].
   - **Relevant patterns:** Guards on has_thermal_data; used by HeatmapPlate3D, TorchWithHeatmap3D.
   - **What we can reuse:** Directly for thermal symmetry (N/S/E/W variance) per frame.
   - **What we should avoid:** None — perfect for thermal micro-feedback.

5. **Feature:** Replay Timeline at `my-app/src/app/replay/[sessionId]/page.tsx`
   - **What it does:** Range slider + Play/Pause; `currentTimestamp` state drives HeatMap, TorchViz3D, etc.
   - **Relevant patterns:** getFrameAtTimestamp; step=10 (10ms).
   - **What we can reuse:** Add colored markers for feedback items; jump-to-frame on click.
   - **What we should avoid:** Blocking main thread with heavy computation on scrub.

6. **Feature:** `TorchViz3D` at `my-app/src/components/welding/TorchViz3D.tsx`
   - **What it does:** 3D torch + weld pool; `angle` and `temp` props; no deviation indication.
   - **Relevant patterns:** Dynamic import, WebGL context-loss handler.
   - **What we can reuse:** Could add optional `isDeviation` or `deviationMessage` prop for visual highlight.
   - **What we should avoid:** Adding extra Canvas — max 1–2 per page (WEBGL_CONTEXT_LOSS.md).

**Existing patterns to follow:**
1. **FeedbackItem contract:** `types/ai-feedback.ts` — severity, message, timestamp_ms, suggestion. Extend with frameIndex, type.
2. **Batch extraction:** `extractHeatmapData(thermal_frames)` filters and transforms in one pass; same pattern for micro-feedback generators.
3. **Replay state:** `currentTimestamp` + `getFrameAtTimestamp` — exact replay; no interpolation.

**Anti-patterns to avoid:**
1. Computing micro-feedback on every scrub — use precomputed array keyed by session.
2. Creating new Canvas for feedback overlay — use existing TorchWithHeatmap3D/HeatmapPlate3D with props.
3. Mutating raw frame data — append-only; feedback is derived.

**Data models/types:**
- `Frame` at `my-app/src/types/frame.ts` — timestamp_ms, volts, amps, angle_degrees, thermal_snapshots, has_thermal_data, heat_dissipation_rate_celsius_per_sec.
- `FeedbackItem` at `my-app/src/types/ai-feedback.ts` — severity, message, timestamp_ms, suggestion (no frameIndex, type).
- `SessionScore`, `ScoreRule` at `my-app/src/lib/api.ts` — session-level only.
- `ThermalSnapshot`, `TemperaturePoint` at `my-app/src/types/thermal.ts` — direction, temp_celsius.

#### Documentation Search

- **CONTEXT.md:** Replay system, HeatmapPlate3D, TorchWithHeatmap3D, rule-based scoring, data models. Max 2 Canvas per page.
- **documentation/WEBGL_CONTEXT_LOSS.md:** 1–2 Canvas instances max; context-loss handlers; no 6+ Canvases.
- **context/ai-report-hardcoded.md:** FeedbackItem, generateAIFeedback, RULE_TEMPLATES.
- **docs/SEAGULL_IMPLEMENTATION_GAP_ANALYSIS.md:** Session-level AI feedback; no frame-level.
- **.cursorrules:** Append-only sensor data; single source of truth; type safety; never mutate raw data.

### 3. Web Research (if applicable)

**Key approaches:**
1. **Moving average for spike detection:** 10–50 frame window; deviation beyond N standard deviations. Common in industrial monitoring.
2. **Thermal symmetry:** Cardinal point variance; >20°C threshold aligns with metallurgical literature on asymmetric heating defects.
3. **Batch processing for long sequences:** Precompute once on session load; store in memory or cache; avoid per-frame work during replay.

---

## THINKING CHECKPOINT #1

### 1. Assumptions (5+)

1. **Assumption:** Welders want frame-level feedback.
   - **If wrong:** Low adoption; feedback ignored.
   - **How to verify:** Pilot user interviews.
   - **Likelihood:** Low. **Impact if wrong:** Medium.

2. **Assumption:** Thresholds can be tuned without ML.
   - **If wrong:** Too many false positives/negatives.
   - **How to verify:** Compare expert vs novice session feedback counts.
   - **Likelihood:** Medium. **Impact if wrong:** High.

3. **Assumption:** Precomputation handles 10k+ frames in <2s.
   - **If wrong:** Slow session load.
   - **How to verify:** Benchmark with 50k-frame session.
   - **Likelihood:** Medium. **Impact if wrong:** High.

4. **Assumption:** FeedbackPanel + timeline markers are sufficient; 3D overlay is optional.
   - **If wrong:** Users want visual 3D cues.
   - **How to verify:** Phase 1 launch without overlay; measure feedback.
   - **Likelihood:** Low. **Impact if wrong:** Low.

5. **Assumption:** Frame index maps 1:1 to timestamp for timeline.
   - **If wrong:** Markers misaligned.
   - **How to verify:** Frames are sorted by timestamp_ms; index = position in array.
   - **Likelihood:** Low. **Impact if wrong:** High.

### 2. Skeptical Engineer Questions (10+)

1. **Q:** Why not just extend SessionScore with per-frame breakdown? **A:** SessionScore is session-level; micro-feedback is a different UX (replay-focused). Separation of concerns.
2. **Q:** Client or server for micro-feedback? **A:** TBD in exploration. Client has frames; server has more CPU. Likely client for MVP to avoid new API.
3. **Q:** What about sessions with gaps in thermal data? **A:** Thermal feedback only on frames with has_thermal_data; skip others.
4. **Q:** How do we avoid alert fatigue? **A:** Severity levels; cap items per type; aggregate similar events.
5. **Q:** Frame index vs timestamp? **A:** frameIndex = array index; timestamp_ms = frame.timestamp_ms. Both useful.
6. **Q:** Does FeedbackPanel need to scroll when scrubbing? **A:** Nice-to-have; highlight active item first.
7. **Q:** Export format for QA? **A:** Defer to Phase 3; CSV/PDF stubs for now.
8. **Q:** Null volts/amps/angle? **A:** Skip frame for that generator; no feedback for missing data.
9. **Q:** Target speed from where? **A:** Expert session median or config; exploration will decide.
10. **Q:** Breaking change to FeedbackItem? **A:** Extend with optional frameIndex, type; existing consumers (WelderReport) can ignore.

### 3. Edge Cases & Failure Modes

**Edge cases:** (1) Empty frames array. (2) All frames null for a sensor. (3) Single-frame session. (4) Thermal data only every 100ms. (5) 50k+ frames — memory/performance.

**Failure modes:** (1) Precompute timeout. (2) Too many items — UI overflow. (3) Timeline markers overlap. (4) WebGL context loss when adding overlay. (5) Threshold too sensitive — noise as alerts.

**Dependencies:** (1) Frame type and thermal structure. (2) Replay page layout. (3) FeedbackPanel component. (4) getFrameAtTimestamp.

### 4. Junior Developer Explanation

Micro-feedback means: when a welder replays their session, instead of only seeing "your overall angle was bad," they see specific messages like "at 42 seconds, your torch angle drifted 12 degrees — try to stay within 5." We compute these by scanning every frame (or every thermal frame) and checking: Is the angle too far from 45°? Is the thermal pattern uneven (north vs south temp)? Is the voltage spiking? Each violation becomes a "feedback item" with a frame number and a message. We show these in the same FeedbackPanel we already use for session-level feedback, and we add colored dots on the replay timeline so the user can click and jump to that moment. We precompute everything when the session loads so scrubbing stays smooth. Phase 1: angle and thermal only. Phase 2: add voltage/amps and speed. Phase 3: cooling rate and session summary.

### 5. Red Team

1. **Too many alerts:** 50 alerts in a 2-minute session overwhelms. **Mitigation:** Cap per type; severity filter; aggregate.
2. **Performance:** 50k frames × 5 generators = slow. **Mitigation:** Batch; web worker; lazy load.
3. **Threshold tuning:** One size doesn't fit all weld types. **Mitigation:** Configurable; Phase 4 refinement.
4. **FeedbackPanel collision:** Session-level + micro-feedback in same panel = confusion. **Mitigation:** Separate sections or tabs.
5. **Timeline marker density:** 20 markers overlap. **Mitigation:** Cluster; show count on hover.

---

## 1. Title

`[Feature] WarpSense Micro-Feedback: Real-Time Frame-Level Guidance for Welding Quality`

- [x] Starts with type tag  
- [x] Specific  
- [x] Under 100 characters  
- [x] Action-oriented  

---

## 2. TL;DR

Welders currently receive only session-level feedback (e.g., "Current fluctuated by 5.2A") after a weld, with no way to pinpoint which moments caused poor quality. This limits the replay feature's value for training and QA — users must guess where problems occurred. The core problem is that we aggregate sensor data into a single score without surfacing frame-level deviations. Today, replay shows heatmaps, 3D torch, and angle charts, but no per-frame guidance. We need to add a micro-feedback engine that detects torch angle drift, thermal asymmetry, voltage/amperage spikes, travel speed deviations, and cooling irregularities — and surfaces these as time-anchored, actionable items in the FeedbackPanel and as colored markers on the Replay Timeline. This aligns with our vision of making replay a proactive training tool that reduces rework and accelerates welder skill development. Estimated effort: large (24–40 hours) across four phased deliveries.

---

## 3. Current State

### A. What's Already Built

**UI Components:**

1. **FeedbackPanel** — `my-app/src/components/welding/FeedbackPanel.tsx`
   - **What it does:** Renders `FeedbackItem[]` with severity styling (info=blue, warning=violet).
   - **Current capabilities:** Message, suggestion, severity (info|warning). Used by WelderReport.
   - **Limitations:** No frameIndex, no type, no "critical" severity; session-level only.
   - **Dependencies:** `FeedbackItem` from `@/types/ai-feedback`.

2. **TorchViz3D** — `my-app/src/components/welding/TorchViz3D.tsx`
   - **What it does:** 3D torch + weld pool; angle and temp props.
   - **Current capabilities:** PBR, OrbitControls, WebGL context-loss handler.
   - **Limitations:** No deviation overlay or highlight.
   - **Dependencies:** @react-three/fiber, drei.

3. **HeatmapPlate3D / TorchWithHeatmap3D** — `my-app/src/components/welding/HeatmapPlate3D.tsx`, `TorchWithHeatmap3D.tsx`
   - **What it does:** 3D thermal plate + torch; uses extractFivePointFromFrame, getFrameAtTimestamp.
   - **Current capabilities:** Thermal vertex displacement, temp→color.
   - **Limitations:** No feedback overlay or deviation highlighting.

4. **Replay page** — `my-app/src/app/replay/[sessionId]/page.tsx`
   - **What it does:** HeatMap, TorchAngleGraph, TorchWithHeatmap3D; timeline slider; Play/Pause.
   - **Current capabilities:** currentTimestamp state; getFrameAtTimestamp; extractHeatmapData, extractAngleData.
   - **Limitations:** No FeedbackPanel; no timeline markers for deviations.

5. **ScorePanel** — `my-app/src/components/welding/ScorePanel.tsx`
   - **What it does:** Fetches SessionScore; displays total + rules.
   - **Current capabilities:** Session-level only.

**API Endpoints:**
- `GET /api/sessions/:id` — Returns Session with frames. No micro-feedback.
- `GET /api/sessions/:id/score` — Returns SessionScore (total, rules). Session-level only.

**Data Models:**
- `Frame` — timestamp_ms, volts, amps, angle_degrees, thermal_snapshots, has_thermal_data, heat_dissipation_rate_celsius_per_sec.
- `FeedbackItem` — severity, message, timestamp_ms, suggestion (no frameIndex, type).
- `SessionScore` — total, rules[] (rule_id, threshold, passed, actual_value).

**Utilities:**
- `extractFivePointFromFrame(frame)` — center, north, south, east, west from thermal_snapshots.
- `extractHeatDissipation(frame)` — heat_dissipation_rate_celsius_per_sec.
- `getFrameAtTimestamp(frames, timestamp)` — nearest frame at or before timestamp.
- `extractHeatmapData(frames, direction)` — HeatmapData for heatmap.
- `extractAngleData(frames)` — AngleData for TorchAngleGraph.

### B. Current User Flows

**Flow 1: Replay Page**
```
User loads /replay/[sessionId]
  → fetchSession, fetchScore
  → useFrameData → thermal_frames, first_timestamp_ms, last_timestamp_ms
  → HeatMap, TorchWithHeatmap3D, TorchAngleGraph render
  → User scrubs timeline; visuals update
  → ScorePanel shows session score (if present)
Current limitation: No per-frame feedback; no timeline markers.
```

**Flow 2: WelderReport**
```
User loads /seagull/welder/[id]
  → fetchSession, fetchScore, fetchExpertSession
  → generateAIFeedback(session, score, historical) → AIFeedbackResult
  → FeedbackPanel(feedback_items) shows session-level rules
  → HeatMap, LineChart render
Current limitation: Feedback is session-level only; no frame index or scrub-to-moment.
```

**Flow 3: Compare Page**
```
User loads /compare/[idA]/[idB]
  → Side-by-side heatmaps + delta
  → Timeline shared; no feedback.
Current limitation: No micro-feedback in compare.
```

### C. Broken/Incomplete User Flows

1. **Flow:** User wants to see "where did I go wrong?" during replay.
   - **Current behavior:** No feedback on replay page; must go to WelderReport for session-level summary.
   - **Why it fails:** Replay has no FeedbackPanel; feedback has no frame anchors.
   - **User workaround:** Manually correlate session feedback with timeline.
   - **Impact:** Inefficient; poor learning.

2. **Flow:** User wants to jump to a specific problematic moment.
   - **Current behavior:** No way to jump from feedback to timeline position.
   - **Why it fails:** FeedbackItem has timestamp_ms: null in practice; no "frame 4200" link.
   - **User workaround:** None.
   - **Impact:** Cannot act on feedback during replay.

3. **Flow:** QA wants frame-level report for audit.
   - **Current behavior:** Only session score + rules; no per-frame export.
   - **Why it fails:** No micro-feedback data model or export.
   - **User workaround:** Manual inspection.
   - **Impact:** Time-consuming QA.

### D. Technical Gaps

- **Frontend:** No micro-feedback generator; no FeedbackItem extension (frameIndex, type); no timeline markers; no jump-to-frame from feedback.
- **Backend:** No frame-level feature extraction; no micro-feedback API.
- **Data:** FeedbackItem not serializable with frameIndex/type; no MicroFeedbackResult type.

### E. Current State Evidence

- **FeedbackItem type:** `my-app/src/types/ai-feedback.ts` lines 26–35.
- **Replay timeline:** `my-app/src/app/replay/[sessionId]/page.tsx` lines 438–482 — range input, no markers.
- **Frame structure:** `my-app/src/types/frame.ts` lines 68–120.
- **extract_features:** `backend/features/extractor.py` — session-level only.

---

## 4. Desired Outcome

### A. User-Facing Changes

**Primary User Flow:**
```
User loads replay
  → Session + frames load
  → Micro-feedback precomputed (angle, thermal in Phase 1)
  → FeedbackPanel shows frame-level items (e.g. "Torch angle drifted 12° at frame 4200 — keep within 5°")
  → Timeline shows colored markers at feedback frames
  → User clicks marker or feedback item → scrubs to that frame
  → 3D/heatmap highlights moment
Success state: User sees and acts on frame-specific guidance.
```

**UI Changes:**
1. **FeedbackPanel:** Extend to show MicroFeedbackItem with frameIndex, type, severity; add "critical" styling (e.g. red border).
2. **Replay Timeline:** Colored markers (dots or segments) at frames with feedback; clickable to jump.
3. **Optional:** TorchViz3D/HeatmapPlate3D — highlight or pulse when active frame has deviation (Phase 2+).

**UX Changes:**
- Feedback items are actionable (click → scrub to frame).
- Timeline visually indicates "problem moments."

### B. Technical Changes

**New types:**
```typescript
// my-app/src/types/micro-feedback.ts
export type MicroFeedbackType = "angle" | "speed" | "thermal" | "cooling" | "voltage";
export type MicroFeedbackSeverity = "info" | "warning" | "critical";

export interface MicroFeedbackItem {
  frameIndex: number;
  severity: MicroFeedbackSeverity;
  message: string;
  suggestion?: string;
  type: MicroFeedbackType;
}
```

**New files:**
- `my-app/src/lib/micro-feedback.ts` — `generateMicroFeedback(frames, options?)` → MicroFeedbackItem[].
- `my-app/src/types/micro-feedback.ts` — types above.
- `my-app/src/utils/micro-feedback-generators.ts` — angleDrift, thermalSymmetry, voltageSpike, etc. (or inline in micro-feedback.ts).

**Modified files:**
- `my-app/src/components/welding/FeedbackPanel.tsx` — Accept MicroFeedbackItem[] or unified; support frameIndex, type; add critical styling.
- `my-app/src/app/replay/[sessionId]/page.tsx` — Call generateMicroFeedback; render FeedbackPanel; add timeline markers; jump-to-frame handler.
- `my-app/src/types/ai-feedback.ts` — Optionally extend FeedbackItem with optional frameIndex, type (or keep separate MicroFeedbackItem).

**Data flow:**
```
frames → generateMicroFeedback(frames) → MicroFeedbackItem[]
  → FeedbackPanel(items)
  → TimelineMarkers(items) → onClick → setCurrentTimestamp(frames[frameIndex].timestamp_ms)
```

### C. Success Criteria (12+)

**User can:**
1. [ ] See frame-level feedback items during replay.
2. [ ] Click a feedback item and scrub to that frame.
3. [ ] See colored markers on the timeline at feedback frames.
4. [ ] Distinguish severity (info/warning/critical) by styling.
5. [ ] See angle drift alerts (e.g. "Torch angle drifted 12° at frame 4200").
6. [ ] See thermal symmetry alerts (e.g. "Thermal asymmetry at frame 3300").

**System does:**
7. [ ] Precompute micro-feedback on session load (no blocking on scrub).
8. [ ] Handle sessions with 10k+ frames (batch; <3s compute).
9. [ ] Skip frames with null sensor data for relevant generators.
10. [ ] Emit MicroFeedbackItem[] with frameIndex, type, severity, message.
11. [ ] Map frameIndex to timestamp for timeline markers.
12. [ ] Not mutate raw frame data.

**Quality:**
- Performance: Precompute <3s for 10k frames.
- Accessibility: FeedbackPanel items keyboard-focusable; timeline markers focusable.
- Browser: Chrome 90+, Firefox 88+, Safari 14+.
- Error handling: Empty frames → []; no crash.

### D. Detailed Verification (Top 5 Criteria)

**Criterion 1: User sees frame-level feedback during replay**
- FeedbackPanel visible on replay page.
- Items show frame index (e.g. "at frame 4200").
- Items grouped or sorted by timestamp/frame.
- Verification: Load replay; assert at least one MicroFeedbackItem when session has deviations.

**Criterion 2: Click feedback item → scrub to frame**
- onClick on item calls setCurrentTimestamp(frames[item.frameIndex].timestamp_ms).
- Timeline slider updates; HeatMap/TorchViz3D update.
- Verification: Click item; assert currentTimestamp matches frame.

**Criterion 3: Timeline markers**
- Markers rendered at positions corresponding to feedback frame timestamps.
- Markers styled by severity (e.g. yellow=warning, red=critical).
- Verification: Assert marker count = feedback count; positions align.

**Criterion 4: Angle drift detection**
- Generator compares angle_degrees to 45° (or configurable target).
- Threshold configurable (e.g. ±5°).
- Verification: Session with angle drift at known frame → item emitted.

**Criterion 5: Thermal symmetry detection**
- Generator uses extractFivePointFromFrame; computes N/S/E/W variance.
- Threshold >20°C (or configurable).
- Only frames with has_thermal_data.
- Verification: Session with thermal asymmetry → item emitted.

---

## 5. Scope Boundaries

### In Scope

1. **MicroFeedbackItem type and generateMicroFeedback engine** — Core model and pure function. Effort: 6–8h.
2. **Angle drift generator** — Per-frame deviation from target angle. Effort: 2–3h.
3. **Thermal symmetry generator** — Per-thermal-frame N/S/E/W variance. Effort: 3–4h.
4. **FeedbackPanel extension** — Support MicroFeedbackItem; frameIndex; severity "critical"; click-to-scrub. Effort: 3–4h.
5. **Replay page integration** — Generate on load; render FeedbackPanel; timeline markers; jump handler. Effort: 4–6h.
6. **Batch precomputation for 10k+ frames** — Single pass; no per-scrub work. Effort: 2–3h.

**Total in-scope:** ~22–28h (Phase 1).

### Out of Scope

1. **Voltage/Amperage generators** — Phase 2. Workaround: Session-level volts_stability in existing score.
2. **Travel speed feedback** — Phase 2; requires speed derivation from frames. Workaround: None yet.
3. **Cooling rate generator** — Phase 3. Workaround: Session-level heat_diss in score.
4. **Session summary / exportable reports** — Phase 3. Workaround: Manual.
5. **3D overlay (TorchViz3D deviation highlight)** — Optional; Phase 4. Workaround: FeedbackPanel + markers.
6. **Configurable thresholds per weld type** — Phase 4. Workaround: Hardcoded thresholds.
7. **Backend micro-feedback API** — Defer; client-side compute for MVP.
8. **WelderReport frame-level integration** — Defer; replay-first.

### Scope Justification

- **Optimizing for:** Speed to market; replay UX; training value.
- **Deferring:** Electrical/speed/cooling (adds complexity); backend API (client has frames); configurable thresholds (tune in Phase 4).

---

## 6. Known Constraints & Context

### Technical Constraints

- **Frame model:** Append-only; no mutation. Field names: angle_degrees, volts, amps, thermal_snapshots, has_thermal_data.
- **WebGL:** Max 1–2 Canvas per page (documentation/WEBGL_CONTEXT_LOSS.md). No new Canvas for feedback overlay without reducing elsewhere.
- **Thermal data:** Sparse — ~1 in 10 frames have thermal_snapshots. Use has_thermal_data guard.
- **Replay state:** currentTimestamp, getFrameAtTimestamp; step=10ms.
- **Browsers:** Chrome 90+, Firefox 88+, Safari 14+.

### Business Constraints

- **Timeline:** Phased; Phase 1 deliverable in 2–3 weeks.
- **Resources:** Single developer assumption.
- **Dependencies:** None blocking.

### Design Constraints

- **FeedbackPanel:** Match existing severity styling; extend for critical (red/amber).
- **Timeline:** Reuse range input; add markers as overlay or adjacent.
- **Accessibility:** WCAG 2.1 Level AA; keyboard navigation for feedback items and markers.

---

## 7. Related Context

### Similar Features

1. **Seagull Pilot / generateAIFeedback** — Session-level FeedbackItem from SessionScore. Reuse FeedbackPanel; extend for frame-level.
2. **extract_features (backend)** — Session aggregates. Pattern for per-frame logic; different output shape.
3. **extractHeatmapData** — Batch transform of frames. Same pattern: single pass, filter, emit structured data.
4. **Replay Timeline** — currentTimestamp state. Add markers; reuse setCurrentTimestamp.

### Related Issues

- `.cursor/issues/seagull-pilot-expansion.md` — Added FeedbackPanel, generateAIFeedback. Micro-feedback extends same UX.
- `.cursor/issues/investor-grade-demo-guided-tour-seagull.md` — Demo polish; micro-feedback could enhance tour.

### Dependency Tree

```
This Issue
  ↑ Depends on: None (Frame, FeedbackPanel, Replay exist)
  ↓ Blocks: Phase 2 (electrical/speed), Phase 3 (cooling/summary)
```

---

## 8. Open Questions & Ambiguities

1. **Client vs server compute?** — Impact: Architecture. Who: Tech lead. When: Exploration. Assumption: Client. Confidence: Medium.
2. **Exact angle threshold?** — Plan says "5°". Impact: Alert frequency. Who: Product. When: Phase 1. Assumption: 5°. Confidence: High.
3. **Thermal variance: N-S only or full N/S/E/W?** — Plan says "cardinal points." Impact: Generator logic. Who: Exploration. Assumption: Max pairwise delta. Confidence: Medium.
4. **Target speed source?** — Expert session median? Config? Impact: Speed generator. Who: Exploration. When: Phase 2. Assumption: Expert median. Confidence: Low.
5. **Moving average window for voltage?** — Plan: 10–50 frames. Impact: Spike detection. Who: Exploration. When: Phase 2. Assumption: 30. Confidence: Low.
6. **Cap on feedback items per session?** — 50? 100? Impact: UX. Who: Product. When: Phase 1. Assumption: 50 per type. Confidence: Low.
7. **Separate FeedbackPanel section for micro vs session?** — Impact: Layout. Who: Design. When: Phase 1. Assumption: Single list, sorted by frame. Confidence: Medium.
8. **Critical severity threshold?** — When is angle "critical" vs "warning"? Impact: Styling. Who: Product. When: Phase 1. Assumption: >15° = critical. Confidence: Low.
9. **Persistence?** — Store computed micro-feedback? Impact: Performance. Who: Exploration. When: Phase 1. Assumption: No; recompute on load. Confidence: High.
10. **Compare page micro-feedback?** — Show for both sessions? Impact: Scope. Who: Product. When: Phase 2. Assumption: Out of scope for Phase 1. Confidence: High.

**Blockers:** None for Phase 1.  
**Important:** #2, #3, #6, #7 — decide before implementation.

---

## 9. Initial Risk Assessment

**Risk #1: Performance — 50k-frame sessions**
- **Description:** Precompute takes >5s; blocks UI.
- **Probability:** 30%. **Impact:** High.
- **Mitigation:** Batch; consider web worker; lazy load FeedbackPanel.
- **Contingency:** Limit to first 20k frames; "Load full feedback" button.

**Risk #2: Threshold tuning — too many false positives**
- **Description:** Alerts on every frame; alert fatigue.
- **Probability:** 40%. **Impact:** Medium.
- **Mitigation:** Cap items; severity filter; Phase 4 tuning.
- **Contingency:** Increase thresholds; add "show only critical."

**Risk #3: FeedbackPanel + session feedback collision**
- **Description:** WelderReport has session feedback; replay adds micro — same component?
- **Probability:** 80%. **Impact:** Low.
- **Mitigation:** Unified item type with optional frameIndex; conditional rendering.
- **Contingency:** Separate MicroFeedbackPanel.

**Risk #4: Timeline marker overlap**
- **Description:** 20+ markers; visual clutter.
- **Probability:** 50%. **Impact:** Medium.
- **Mitigation:** Cluster nearby; show count; tooltip.
- **Contingency:** Collapse to severity-colored regions.

**Risk #5: Thermal data sparsity**
- **Description:** 1 in 10 frames; gaps in thermal feedback.
- **Probability:** 100%. **Impact:** Low.
- **Mitigation:** Expected; only thermal frames get thermal feedback.
- **Contingency:** None.

**Risk #6: WebGL — adding overlay**
- **Description:** New 3D overlay consumes Canvas; context loss.
- **Probability:** 20%. **Impact:** High.
- **Mitigation:** Optional overlay; no new Canvas; use existing TorchWithHeatmap3D props.
- **Contingency:** Skip 3D overlay.

**Risk #7: Null sensor handling**
- **Description:** Frames with null volts/amps/angle; generators crash.
- **Probability:** 10%. **Impact:** High.
- **Mitigation:** Guard every generator; skip null.
- **Contingency:** Defensive checks in each generator.

**Risk #8: Scope creep — Phase 2 features**
- **Description:** Voltage/speed/cooling requested before Phase 1 ships.
- **Probability:** 30%. **Impact:** Medium.
- **Mitigation:** Clear phase boundaries; document in issue.
- **Contingency:** Push Phase 2 to next sprint.

**Top 3 Risks:** #2 (threshold tuning), #4 (marker overlap), #1 (performance).

---

## 10. Classification & Metadata

**Type:** feature  
**Priority:** P2 (Normal)  
**Effort:** Large (24–40h total; Phase 1: ~24h)  
**Category:** Fullstack (frontend-heavy; potential backend in Phase 2+)  
**Tags:** user-facing, high-impact, needs-research

**Priority justification:**  
Micro-feedback advances training/QA value proposition and differentiates replay from passive playback. Not blocking core MVP (replay works today); no P0/P1 production break. Fits Q2 product vision of "portable, actionable replay." Estimated 24–40h across phases; Phase 1 deliverable in 2–3 weeks.

**Effort breakdown:**
- Frontend (generators, types, FeedbackPanel, replay integration): 16–20h  
- Testing: 4–6h  
- Documentation: 2h  
- **Total Phase 1:** ~24h. **Confidence:** Medium (generator logic has unknowns).

---

## 11. Strategic Context

**Product roadmap fit:**  
Q2 goal of "actionable replay" and "training tool" — micro-feedback is core enabler. Converts passive replay into guided learning.

**Capabilities unlocked:**
1. **Real-time coaching UI** — Future: live welding with frame-level alerts.
2. **QA audit trail** — Frame-level export for compliance.
3. **Threshold tuning dashboard** — Phase 4: per-yard configuration.

**User feedback themes:**
- "Where did I mess up?" — Addressed by frame-anchored items.
- "Can I jump to the bad spot?" — Addressed by click-to-scrub.
- "Too many alerts" — Mitigated by severity, caps, Phase 4 tuning.

**Impact metrics:**
- **Users:** All replay/demo users.
- **Frequency:** Every replay session.
- **Value:** Faster skill uptake; lower rework; QA efficiency.
- **Technical:** Reduces technical debt by formalizing frame-level analysis (vs ad-hoc).

---

## THINKING CHECKPOINT #2

### Self-Critique

1. **New team member clarity:** (1) "MicroFeedbackItem" vs "FeedbackItem" — explain. (2) "frameIndex" — 0-based? (3) Phase boundaries — add to TL;DR. (4) Timeline marker UI — needs mockup. (5) "Batch precompute" — where stored?
2. **Explorer questions:** Answered in Open Questions; exploration will resolve client vs server, thresholds.
3. **Quantification:** Session sizes (10k), thresholds (5°, 20°C), effort (24–40h) — sufficient.
4. **Evidence:** Code paths, types, file references — sufficient.
5. **Failure:** 8 risks; mitigations listed.
6. **Strategic connections:** Q2 roadmap, training, QA — 3+.
7. **Detail:** ~3500 words — meets 3000+.
8. **Assumptions:** 5+ documented.

### Final Verification

- [x] Pre-issue thinking completed  
- [x] Title specific  
- [x] TL;DR 5–7 sentences  
- [x] Current state exhaustive  
- [x] Desired outcome explicit  
- [x] Scope boundaries clear  
- [x] Constraints documented  
- [x] Related context provided  
- [x] Open questions 10+  
- [x] Risks 8+  
- [x] Classification justified  
- [x] Strategic context explained  
- [x] 12+ acceptance criteria  
- [x] 3000+ words  

---

## After Issue Creation

**Immediate next steps:**
1. Share with stakeholder for validation
2. Answer blocker questions (thresholds, caps)
3. Schedule exploration session
4. Proceed to **Phase 2: Explore Feature** (45–90 min)

**This issue is the foundation for exploration and planning.**
