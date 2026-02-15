
Created a `CONTEXT.md` at the project root and filled it with your actual WarpSense project details.

**It includes:**

- **Project Overview:** WarpSense MVP, monorepo, purpose and milestones
- **Architecture:** Client–server pattern, main design decisions (heatmap = CSS grid, playback = setInterval, etc.)
- **Implemented Features:** 3D viz, replay, heatmap, session comparison, scoring, browser-only demo, utilities
- **Data Models:** Session, Frame, ThermalSnapshot, FrameDelta with relevant fields
- **Patterns:** Frame resolution, SSR safety, thermal carry-forward, WebGL context limits
- **Integration Points:** API endpoints, data flow, main components
- **Constraints:** Data integrity, timing/limits, SSR, sparse thermal, bundle size, WebGL limits
- **File Structure:** Real paths under `my-app/` and `backend/`
- **API Contracts:** Existing session/frames/score endpoints
- **Component APIs:** TorchViz3D, HeatMap, TorchAngleGraph
- **Not Implemented / Rejected:** Including WebGL context limit and Recharts heatmap
- **AI Prompting Patterns:** How to use `@CONTEXT.md` for adding features and debugging

You can now reference `@CONTEXT.md` in Cursor prompts so AI tools have a single, up-to-date project reference. Update it when you add features or change architecture.
