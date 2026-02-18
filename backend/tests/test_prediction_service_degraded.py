"""
Unit test for prediction service degraded mode.
Mocks MODEL_PATH.exists() = False to avoid manual backend restart.
"""
import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_degraded_mode_when_onnx_missing():
    """When ONNX file does not exist, predict_warp_risk returns model_available=False."""
    import services.prediction_service as ps

    # Clear cached session so _get_session re-evaluates
    ps._session = None

    with patch.object(ps.MODEL_PATH, "exists", return_value=False):
        frames = [
            {
                "angle_degrees": 45,
                "amps": 150,
                "volts": 22,
                "thermal_snapshots": [{"readings": []}],
            }
        ] * 50
        r = ps.predict_warp_risk(frames)

    assert r["model_available"] is False
    assert r["probability"] == 0.0
    assert r["risk_level"].value == "ok"
