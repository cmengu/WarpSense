
Refinements from the latest critique are applied. The plan file is updated with all minor fixes.

**Applied refinements**

1. **Step 1.1 / 1.4 overlap** – Step 1.1 notes that Step 1.4 adds four distinct test cases. Step 1.4 is described as “Consolidates with Step 1.1 verification” and lists those four test cases explicitly.

2. **Step 2.2 Escape key** – Replaced backdrop `onKeyDown` with a document-level Escape listener so Escape works when focus is on Next or Skip:
   ```ts
   useEffect(() => {
     const h = (e: KeyboardEvent) => e.key === 'Escape' && handleSkip();
     document.addEventListener('keydown', h);
     return () => document.removeEventListener('keydown', h);
   }, [handleSkip]);
   ```
   - Added Common Failures entry describing the Escape focus issue and this fix.

3. **Step 2.3 DemoTour mount timing** – DemoTour now mounts only when sessions exist: `showTour && sessions && <DemoTour ... />`. Red team section updated to reflect this.

4. **Step 3.2 AppNav** – Clarified that `aria-current` applies only when `pathname?.startsWith('/seagull')`, and that `/demo/team` uses a different layout without AppNav.

5. **Step 1.3 heatmap test** – Added optional automated test: mock `getDemoTeamData` with frames that lack `thermal_snapshots` and assert the HeatMap fallback or “No thermal data” appears.

6. **Step 3.3** – Updated description to note that Escape is handled by a document-level listener and works when focus is on buttons.
