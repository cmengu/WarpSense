"""
loader_esp32.py is a stub that fails loudly until real ESP32 captures exist, so mock data can never silently stand in for real sessions (Gate 0 / D4).

When real captures exist, this loads persisted sessions (Frame lists from the
POST /sessions path) and routes them through the SAME frames_to_session_tensor
used by loader_mock, with source="esp32".

For newcomers: an intentionally empty placeholder. It exists so the codebase
already has the correct entry point for real sensor data, but it raises
immediately — a loud failure is safer than quietly substituting mock data and
letting fake numbers masquerade as real results (the D4 principle).
"""


def load_esp32_sessions(*args, **kwargs):
    raise NotImplementedError(
        "No real ESP32 captures exist yet (Gate 0 pending). "
        "See STEPS.md Step P1 / FUTURE_PLANS_WORLD_MODELS.md Gate 0."
    )
