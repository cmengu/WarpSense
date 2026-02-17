
All five minor refinements from the critique are now in the implementation plan:

1. **Step 3.5 makeThermalSnapshot** – Uses positional args `(center, north, south, east, west)` and `thermal_snapshots` (array). Example: `makeThermalSnapshot(400, 100, 60, 80, 75)` for N-S delta 40°C.

2. **Step 3.1 jest.mock** – Documented that the micro-feedback module must be mocked and added `jest.mock('@/lib/micro-feedback', () => ({ generateMicroFeedback: jest.fn() }))` before the import.

3. **Step 2.3 key format** – Picked a single recommended format and put it in a code block:  
   `key = frameIndex != null ? \`fb-${frameIndex}-${item.type ?? 'session'}\` : \`${severity}-${i}-${message.slice(0,40)}\``

4. **Step 1.7 makeThermalSnapshot signature** – Added explicit signature:  
   `(center: number, north: number, south: number, east: number, west: number) => ThermalSnapshot` — positional args only.

5. **Step 3.2 loading state** – Added explicit conditional for the loading state:  
   `{sessionData != null && <FeedbackPanel items={microFeedback} frames={sessionData.frames} onFrameSelect={handleFrameSelect} />}` to avoid showing “No feedback” before data loads.
