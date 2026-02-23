"""
Warp prediction service.
Loads ONNX model at startup; exposes predict_warp_risk().
Degrades gracefully when model file does not exist.

ONNX output: result[1][i][1] = P(class=1) = P(will_breach).
Sessions with < 50 frames receive default-feature prediction (may be poorly calibrated).
"""
import logging
from pathlib import Path
from typing import Optional

from models.shared_enums import RiskLevel
from features.warp_features import extract_features, features_to_array, FEATURE_COLS

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "warp_model.onnx"
WARNING_THRESHOLD = 0.55
CRITICAL_THRESHOLD = 0.75

_session: Optional[object] = None


def _get_session():
    global _session
    if _session is None:
        if not MODEL_PATH.exists():
            logger.warning("warp_model.onnx not found — prediction service degraded")
            return None
        try:
            import onnxruntime as ort

            _session = ort.InferenceSession(str(MODEL_PATH))
            logger.info("Warp prediction model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load warp model: %s", e)
            return None
    return _session


def predict_warp_risk(frame_window: list[dict]) -> dict:
    """
    Returns { probability, risk_level, model_available }.
    risk_level ∈ ("ok", "warning", "critical").
    Handles empty/short windows via extract_features default values.
    Catches AttributeError (e.g. thermal_snapshots[0]=None), KeyError, TypeError, ValueError.
    """
    sess = _get_session()
    if sess is None:
        return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": False}

    try:
        features = extract_features(frame_window)
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        logger.error("extract_features failed for warp prediction: %s", e)
        return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": True}

    try:
        try:
            import numpy as np  # Lazy import: avoids hard import-time failures in non-ML codepaths
        except Exception as e:
            logger.error("NumPy unavailable for warp prediction: %s", e)
            return {
                "probability": 0.0,
                "risk_level": RiskLevel.OK,
                "model_available": False,
            }

        X = np.array([features_to_array(features)], dtype=np.float32)
        input_name = sess.get_inputs()[0].name
        result = sess.run(None, {input_name: X})
        prob = float(result[1][0][1])

        if prob >= CRITICAL_THRESHOLD:
            level = RiskLevel.CRITICAL
        elif prob >= WARNING_THRESHOLD:
            level = RiskLevel.WARNING
        else:
            level = RiskLevel.OK

        return {
            "probability": round(prob, 4),
            "risk_level": level,
            "model_available": True,
        }
    except Exception as e:
        logger.error("predict_warp_risk inference error: %s", e)
        return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": False}
