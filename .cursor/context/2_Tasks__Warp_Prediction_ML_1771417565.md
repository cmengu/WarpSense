
Summary of the **Agent 2 Warp Prediction ML Batch 1** implementation:

---

## Implementation status

The feature is implemented end-to-end. Current state:

### Backend

| Component | Status | Location |
|-----------|--------|----------|
| Training data generation | Done | `backend/scripts/generate_training_data.py` |
| Model training (sklearn → ONNX) | Done | `backend/scripts/train_warp_model.py` |
| Prediction service | Done | `backend/services/prediction_service.py` |
| Shared warp features | Done | `backend/features/warp_features.py` |
| Predictions route | Done | `backend/routes/predictions.py` |
| `get_session_frames_raw` helper | Done | `backend/routes/sessions.py` (lines 69–89) |
| Router registration | Done | `backend/main.py` (lines 72–75) |

### Frontend

| Component | Status | Location |
|-----------|--------|----------|
| Types | Done | `my-app/src/types/prediction.ts` |
| `fetchWarpRisk` API | Done | `my-app/src/lib/api.ts` (lines 384–397) |
| WarpRiskGauge | Done | `my-app/src/components/welding/WarpRiskGauge.tsx` |
| Replay page wiring | Done | `my-app/src/app/replay/[sessionId]/page.tsx` (lines 31–35, 139, 397–326, 449–456) |

### Merge files

| File | Purpose |
|------|---------|
| `_merge/agent2_main.py` | Instructions for adding predictions router to main.py |
| `_merge/agent2_api.ts` | Instructions for adding `fetchWarpRisk` to api.ts |

---

## Verification checklist

To run the verification steps locally:

1. **Generate training data**
   ```bash
   cd /Users/ngchenmeng/test && PYTHONPATH=. python -m backend.scripts.generate_training_data --output data/training_data.csv
   ```

2. **Train the model**
   ```bash
   python -m backend.scripts.train_warp_model --input data/training_data.csv --output backend/models/warp_model.onnx
   ```

3. **Seed the database** (if not already done)
   ```bash
   curl -X POST http://localhost:8000/api/dev/seed-mock-sessions
   ```
   Note: `sess_novice_001` is created by the dev seed API. `seed_demo_data.py` creates IDs like `sess_mike-chen_001`.

4. **Test warp-risk endpoint**
   ```bash
   curl -s http://localhost:8000/api/sessions/sess_novice_001/warp-risk | jq .
   ```

5. **Degraded mode** (with no ONNX file): the endpoint should return `{ "model_available": false }`.

6. **Frontend build**
   ```bash
   cd my-app && npm run build
   ```

7. **WarpRiskGauge tests** – `my-app/src/__tests__/components/welding/WarpRiskGauge.test.tsx` covers:
   - Model unavailable state
   - Probability display (ok)
   - Warning styling (amber)
   - Critical styling (red)

---

## Details

- **Risk levels**: `ok`, `warning`, `critical` with thresholds at 0.55 and 0.75.
- **Graceful degradation**: If `warp_model.onnx` is missing or loading fails, the service returns `model_available: false` and `risk_level: "ok"`.
- **Replay page**: WarpRiskGauge is shown for the primary session; a 10s timeout handles slow or failing warp-risk fetches.
