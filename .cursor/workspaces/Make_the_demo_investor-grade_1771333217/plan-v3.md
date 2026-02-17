
All requested refinements are in place.

**Updates applied:**

1. **Step 3.3 verification**  
   Updated from `fireEvent.keyDown(backdrop, { key: 'Escape' })` to `fireEvent.keyDown(document, { key: 'Escape' })` and clarified that the listener is document-level.

2. **Path convention**  
   Added under the Pre-Flight Checklist:  
   *"All file paths (e.g., `app/demo/team/page.tsx`) are relative to the project root. Run `npm install`, `npm test`, and `npm run dev` from `my-app/`."*

3. **Step 1.3 implementer note**  
   Added:  
   *"`tempToColorRange(minT, maxT)` correctly handles `allTemps.length === 0` via the 0/600 fallbacks above."*

4. **Rollback section**  
   Added Section 8 with explicit rollback steps for new and modified files and tests.
