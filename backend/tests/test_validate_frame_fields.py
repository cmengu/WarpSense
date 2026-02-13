"""
Step 7 verification test for validate_frame_fields.py.

Verification result (when PASS):
  - required_keys_present: angle_degrees, amps, has_thermal_data in Frame.model_dump()
  - prohibited_keys_absent: torch_angle_degrees, frame_type NOT in keys
  - validate_frame_keys_accepts_valid: validate_frame_keys(Frame) does not raise
  - validate_frame_keys_rejects_missing: Frame missing required key raises AssertionError

If FAIL: Assertion error indicates wrong field names — fix models/frame.py.
"""

import pytest

from models.frame import Frame
from scripts.validate_frame_fields import (
    PROHIBITED_KEYS,
    REQUIRED_KEYS,
    validate_frame_keys,
)


def _make_valid_frame() -> Frame:
    """Frame with all required fields present. has_thermal_data is computed from thermal_snapshots."""
    return Frame(
        timestamp_ms=0,
        volts=22.0,
        amps=150.0,
        angle_degrees=45.0,
        thermal_snapshots=[],
    )


@pytest.fixture
def valid_frame() -> Frame:
    return _make_valid_frame()


class TestValidateFrameFields:
    """Step 7 verification: frame field names match scoring contract."""

    def test_required_keys_in_model_dump(self, valid_frame: Frame) -> None:
        """Required: angle_degrees, amps, has_thermal_data present in model_dump()."""
        keys = set(valid_frame.model_dump().keys())
        assert REQUIRED_KEYS <= keys, f"Missing required keys: {REQUIRED_KEYS - keys}"

    def test_prohibited_keys_not_in_model_dump(self, valid_frame: Frame) -> None:
        """Prohibited: torch_angle_degrees, frame_type must NOT exist."""
        keys = set(valid_frame.model_dump().keys())
        assert not (PROHIBITED_KEYS & keys), f"Prohibited keys present: {PROHIBITED_KEYS & keys}"

    def test_validate_frame_keys_accepts_valid_frame(self, valid_frame: Frame) -> None:
        """validate_frame_keys(Frame) does not raise for correct model."""
        validate_frame_keys(valid_frame)

    def test_validate_frame_keys_rejects_missing_required(self) -> None:
        """Frame missing required key raises AssertionError."""
        # Create a dict that looks like a frame but is missing angle_degrees
        # We cannot create a Frame without required schema - but we can test
        # that the validation logic rejects a fake frame-like object.
        # Instead: test that our Frame HAS the keys (already in test_required_keys).
        # For "rejects missing" we'd need a way to get model_dump with a key removed.
        # The Frame model always includes all fields in model_dump - optional ones
        # may be None. So the only way to get "missing" is to pass a different model.
        # Let's create a minimal class that mimics Frame but has wrong keys:
        class BadFrame:
            def model_dump(self):
                return {"amps": 150, "has_thermal_data": False}
                # Missing angle_degrees

        with pytest.raises(AssertionError, match="missing required"):
            validate_frame_keys(BadFrame())  # type: ignore[arg-type]

    def test_validate_frame_keys_rejects_prohibited(self) -> None:
        """Frame with prohibited key raises AssertionError."""
        class BadFrameWithProhibited:
            def model_dump(self):
                return {
                    "angle_degrees": 45.0,
                    "amps": 150.0,
                    "has_thermal_data": False,
                    "torch_angle_degrees": 50.0,
                }

        with pytest.raises(AssertionError, match="deprecated|must NOT"):
            validate_frame_keys(BadFrameWithProhibited())  # type: ignore[arg-type]
