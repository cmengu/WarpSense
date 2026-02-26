"""
Rolling buffer for speed_change_pct. Same formula as calibrate_alert_thresholds (Step 0c).

Formula: speed_change_pct = (current_speed - speed_10_frames_ago) / speed_10_frames_ago * 100
when speed_10_frames_ago > 0; else 0. Negative = deceleration.
"""

from collections import deque
from typing import Deque, Optional, Tuple


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


class VoltageSustainBuffer:
    """Tracks (timestamp_ms, voltage). Detects voltage < threshold sustained > duration_ms.
    Uses timestamp_ms only — frame-rate independent. Push every frame to maintain state;
    when voltage_V is None, buffer resets and returns False.
    """

    def __init__(self, threshold_V: float, duration_ms: float) -> None:
        self._threshold = threshold_V
        self._duration_ms = duration_ms
        self._low_since_ms: Optional[float] = None

    def push(self, timestamp_ms: float, voltage_V: Optional[float]) -> bool:
        """Record sample. Returns True if sustained low for >= duration_ms this frame."""
        if voltage_V is None or voltage_V >= self._threshold:
            self._low_since_ms = None
            return False
        if self._low_since_ms is None:
            self._low_since_ms = timestamp_ms
        elapsed = timestamp_ms - self._low_since_ms
        return elapsed >= self._duration_ms

    def reset(self) -> None:
        """Clear state. Call on session start (or implicitly via fresh engine)."""
        self._low_since_ms = None


class CurrentRampDownBuffer:
    """Detects abrupt current drop to zero (crater crack). Arms only after arc on >= arc_on_min_ms."""

    def __init__(
        self,
        ramp_pct: float,
        ramp_min_ms: float,
        arc_on_min_ms: float,
        max_history_ms: float = 1000.0,
    ) -> None:
        self._ramp_pct = ramp_pct
        self._ramp_min_ms = ramp_min_ms
        self._arc_on_min_ms = arc_on_min_ms
        self._max_history_ms = max_history_ms
        self._samples: Deque[Tuple[float, float]] = deque()
        self._arc_on_since_ms: Optional[float] = None

    def push(self, timestamp_ms: float, amps: Optional[float]) -> Optional[bool]:
        """
        Returns True if abrupt (crater crack), False if controlled, None if arc on or not armed.
        Arms only after amps > 1.0 for >= arc_on_min_ms.
        """
        if amps is None:
            return None
        self._samples.append((timestamp_ms, amps))
        while self._samples and (timestamp_ms - self._samples[0][0]) > self._max_history_ms:
            self._samples.popleft()
        if amps > 1.0:
            if self._arc_on_since_ms is None:
                self._arc_on_since_ms = timestamp_ms
            return None
        self._arc_on_since_ms = None
        arc = [(t, a) for t, a in self._samples if a > 1.0]
        if not arc:
            return None
        arc_duration = arc[-1][0] - arc[0][0]
        if arc_duration < self._arc_on_min_ms:
            return None
        for i, (t1, a1) in enumerate(arc):
            for t2, a2 in arc[i + 1 :]:
                if t2 - t1 >= self._ramp_min_ms and a2 <= a1 * (1 - self._ramp_pct / 100):
                    return False
        return True

    def reset(self) -> None:
        """Clear state."""
        self._samples.clear()
        self._arc_on_since_ms = None
