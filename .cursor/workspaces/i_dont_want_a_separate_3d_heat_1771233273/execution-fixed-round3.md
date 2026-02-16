
Round 3 fixes are done. Here’s what changed:

## Round 3 Fixes Applied

### LOW (optional) – dependency arrays

**1. `loadComparison` `useEffect` dependency array**  
- **File:** `my-app/src/app/replay/[sessionId]/page.tsx`  
- **Change:** Added `COMPARISON_SESSION_ID` to the dependency array (line 295).  
- **Reason:** The effect uses `COMPARISON_SESSION_ID` inside its callback, so it should be in the dependency list.

**2. Score-fetch `useEffect` dependency array**  
- **File:** Same file  
- **Change:** Added `COMPARISON_SESSION_ID` to the dependency array (line 343).  
- **Reason:** This effect also uses `COMPARISON_SESSION_ID` for the comparison score fetch.

---

## Verification

- **Linter:** No issues in `my-app/src/app/replay/[sessionId]/page.tsx`.

Please run:

```bash
cd my-app
npm test -- --run
npx eslint src/app/replay/ src/app/demo/ src/components/welding/ src/utils/heatmapShaderUtils.ts src/utils/thermalInterpolation.ts src/constants/thermal.ts
```

And do the manual checks:

1. `/demo` – torch + thermal metal, legend, scrubbing  
2. `/replay/[sessionId]` – two 3D views and heat  
3. `NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID=` (empty) – comparison disabled  
4. `maxTemp={0}` – no GPU errors (shader guards against division by zero)
