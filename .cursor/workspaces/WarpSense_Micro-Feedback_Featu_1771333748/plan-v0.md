
Summary of the implementation blueprint:

---

## WarpSense Micro-Feedback Implementation Plan

Created implementation plan at **`.cursor/plans/warpsense-micro-feedback-implementation-plan.md`**.

### Structure

**Pre-planning (≈30 min):**
- **Exploration review** – Core approach, main decisions, components, data flow, risks, gaps
- **Dependency brainstorm** – 20 work items, dependency graph, critical path, parallel work
- **Risk-based planning** – Failure modes, mitigations, contingency steps

**3 phases, 27 steps (~18 hours)**

| Phase | Steps | Est. | Main deliverable |
|-------|-------|------|------------------|
| **1. Foundation** | 7 | 5.5h | Types, `lib/micro-feedback.ts`, migrated tests |
| **2. FeedbackPanel** | 7 | 4h | Critical severity, `onFrameSelect`, frameIndex handling |
| **3. Replay** | 13 | 8.5h | FeedbackPanel, timeline markers, click-to-scrub |

### Step coverage

- **5 critical steps** with full code (e.g. Step 1.3 `lib/micro-feedback.ts`)
- **22 non-critical steps** with subtasks and verification
- **Common failures & fixes** for critical steps (Step 1.3, 2.2, 3.3)

### Quality assurance

1. **Verification tests** – Each step has setup, actions, expected results, and pass criteria
2. **Risk heatmap** – 10+ risks, with probability/impact and mitigations
3. **Success criteria** – 14 P0/P1 checks with verification methods
4. **Pre-flight checklists** – 3 phases, ~12 items
5. **Red team** – 10 issues, with fixes
6. **Implementability test** – 10 likely junior-developer questions and answers
7. **Bus factor** – 6 items for handoff
8. **Progress tracking** – Dashboard, standup template, velocity tracking

### Main design choices (from exploration)

- **Client-side** – `generateMicroFeedback(frames)` in the browser
- **Extended FeedbackItem** – optional `frameIndex` and `type`
- **Thresholds** – 45° target, ±5° warning, ±15° critical; 20°C thermal
- **Cap** – 50 items per type
- **No 3D overlay** – WebGL limit; FeedbackPanel + timeline markers only

### Next steps

1. **Review** – Walk through with stakeholder (~30 min)
2. **Environment** – Run Phase 1 pre-flight checklist
3. **Implementation** – Start with Step 1.1 (create `types/micro-feedback.ts`)
