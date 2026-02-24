"""
Rolling buffer for speed_change_pct. Same formula as calibrate_alert_thresholds (Step 0c).

Formula: speed_change_pct = (current_speed - speed_10_frames_ago) / speed_10_frames_ago * 100
when speed_10_frames_ago > 0; else 0. Negative = deceleration.
"""

from collections import deque


class SpeedFrameBuffer:
    """Maintains last 11 speed values for 10-frame lookback."""

    def __init__(self) -> None:
        self._speeds: deque[float] = deque(maxlen=11)

    def push(self, speed_mm_per_min: float) -> None:
        """Append one speed value."""
        self._speeds.append(speed_mm_per_min)

    def speed_change_pct(self) -> float | None:
        """Percent change vs 10 frames ago. None if < 10 frames buffered."""
        if len(self._speeds) < 11:
            return None
        current = self._speeds[-1]
        speed_10_ago = self._speeds[0]
        if speed_10_ago <= 0:
            return 0.0
        return (current - speed_10_ago) / speed_10_ago * 100.0
