"""
WarpSense AI tool definitions for FunctionGemma on-device inference.

Defines WARP_TOOLS: check_parameter_threshold, evaluate_session_score, flag_anomaly.
Used by function_gemma.generate_hybrid and weld_demo. Parameter enum constrains
270M to prevent hallucinated param names (wire_feed, etc.).
"""

# Single source of truth for allowed parameters. Used by _validate_tool_call
# in function_gemma to reject hallucinated values (e.g. "wire_feed").
ALLOWED_PARAMETERS = frozenset({"voltage", "current", "angle"})

WARP_TOOLS = [
    {
        "name": "check_parameter_threshold",
        "description": "Check if a welding parameter (voltage, current, or angle) is within acceptable range.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {
                    "type": "string",
                    "enum": ["voltage", "current", "angle"],
                    "description": "Parameter name: voltage, current, or angle.",
                },
                "value": {
                    "type": "number",
                    "description": "Measured value (e.g. 28 for 28V, 52 for 52 degrees).",
                },
                "min": {
                    "type": "number",
                    "description": "Minimum acceptable value.",
                },
                "max": {
                    "type": "number",
                    "description": "Maximum acceptable value.",
                },
            },
            "required": ["parameter", "value", "min", "max"],
        },
    },
    {
        "name": "evaluate_session_score",
        "description": "Evaluate welding session quality score. Use when session ID (WS-NNN) and score are mentioned.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID matching WS-NNN pattern (e.g. WS-042).",
                },
                "score": {
                    "type": "number",
                    "description": "Session quality score (0-100).",
                },
            },
            "required": ["session_id", "score"],
        },
    },
    {
        "name": "flag_anomaly",
        "description": "Flag an anomaly or issue in welding parameters or session.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID if applicable (WS-NNN).",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief reason for flagging.",
                },
            },
            "required": [],
        },
    },
]
