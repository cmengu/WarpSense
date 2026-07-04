"""
ESP32 real-capture loader — STUB until Gate 0 lands real sessions.

When real captures exist, this loads persisted sessions (Frame lists from the
POST /sessions path) and routes them through the SAME frames_to_session_tensor
used by loader_mock, with source="esp32". Failing loudly here is deliberate:
nothing may silently substitute mock data for real (D4 / Gate 0 principle).
"""


def load_esp32_sessions(*args, **kwargs):
    raise NotImplementedError(
        "No real ESP32 captures exist yet (Gate 0 pending). "
        "See STEPS.md Step P1 / FUTURE_PLANS_WORLD_MODELS.md Gate 0."
    )
