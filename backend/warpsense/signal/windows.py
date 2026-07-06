"""
Window sizes, in frames, all assuming the 100 Hz sensor stream (10 ms/frame).

If the sample rate ever changes, these change together — that is why they
live in one file instead of three.
"""

WINDOW_1S_FRAMES = 100
# 1-second rolling window: classifier's heat_input_min_rolling,
# angle_max_drift_1s, heat_diss_max_spike.

POROSITY_WINDOW_FRAMES = 30
# Tumbling voltage-sigma window for the floor's porosity_event_count.

WQI_WINDOW_FRAMES = 50
# Tumbling window for the floor's per-window WQI timeline (0.5 s).
