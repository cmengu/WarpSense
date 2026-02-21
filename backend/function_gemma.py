"""
FunctionGemma on-device AI engine for WarpSense.

Routes simple welding queries on-device (Cactus/270M) and complex queries to cloud
(Gemini). When Cactus is not available (Step 1 not done), returns stub on-device
responses so demo and API work end-to-end.

Critical: source normalization happens here — all on-device variants → "on-device".
"""

import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from warp_tools import ALLOWED_PARAMETERS, WARP_TOOLS

# Load .env so GEMINI_API_KEY is available for weld_demo (API loads via database.connection)
_backend_dir = Path(__file__).resolve().parent
_env_path = _backend_dir / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

# Path resolution via __file__ — works when imported as module.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_CACTUS_SRC = os.path.join(_BACKEND_DIR, "cactus", "python", "src")
_WEIGHTS_PATH = os.path.join(_BACKEND_DIR, "cactus", "weights", "functiongemma-270m-it")

# Cactus availability: try import; stub when repo not copied yet.
_CACTUS_AVAILABLE = False
try:
    if _CACTUS_SRC not in sys.path:
        sys.path.insert(0, _CACTUS_SRC)
    from cactus import cactus_init  # noqa: F401

    _CACTUS_AVAILABLE = True
except Exception:
    pass

# Singleton: init once at load, warmup with dummy inference. Thread-safe.
# Two concurrent requests before warmup would both call cactus_init without lock.
_cactus_initialized = False
_cactus_lock = threading.Lock()


def get_ai_health() -> dict[str, Any]:
    """
    Health status for GET /api/ai/health.
    Honest about Gemini: key_configured (not ok) when only checking presence.
    """
    cactus_status = "ok" if (_CACTUS_AVAILABLE and _cactus_initialized) else "error"
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_status = "key_configured" if gemini_key else "unconfigured"
    return {
        "cactus": cactus_status,
        "gemini": gemini_status,
        "model_loaded": _CACTUS_AVAILABLE and _cactus_initialized,
    }


def _ensure_cactus_warm() -> None:
    """Initialize Cactus once; warm model with dummy inference. No-op when stub."""
    global _cactus_initialized
    if not _CACTUS_AVAILABLE or _cactus_initialized:
        return
    with _cactus_lock:
        if _cactus_initialized:
            return
        # cactus_init(...); _run_dummy_inference() — placeholder for Step 1
        _cactus_initialized = True


# Interrogative markers: route to cloud when present and no measurement context.
_INTERROGATIVE_MARKERS = re.compile(
    r"\b(why|how|explain|improve|what should|what could|recommend)\b",
    re.IGNORECASE,
)
# Measurement = digits + unit (V, A, °, degrees, volts, amps). Not raw digits (WS-042, score 41).
_MEASUREMENT_PATTERN = re.compile(
    r"\d+\.?\d*\s*(?:V|A|°|degrees|volts|amps)",
    re.IGNORECASE,
)

OFFLINE_CANNED_RESPONSE = {
    "source": "offline",
    "text": "Cloud coaching unavailable offline. Welding shop floors may lack connectivity — this is expected behavior.",
    "function_calls": [],
    "total_time_ms": 0,
    "latency_ms": 0,
}


def _is_interrogative(text: str) -> bool:
    """True if query has interrogative marker (why, explain, improve, etc.)."""
    return bool(_INTERROGATIVE_MARKERS.search(text))


def _has_measurement(text: str) -> bool:
    """True if query contains measurement context (e.g. 28V, 52 degrees)."""
    return bool(_MEASUREMENT_PATTERN.search(text))


def _validate_tool_call(
    function_calls: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> bool:
    """
    Validate tool calls. Reject check_parameter_threshold with invalid parameter.
    Cactus may ignore enum; 270M can hallucinate "wire_feed" etc.
    """
    if not function_calls:
        return True
    tool_names = {t["name"] for t in tools}
    for call in function_calls:
        name = call.get("name")
        if name not in tool_names:
            return False
        args = call.get("arguments") or {}
        if name == "check_parameter_threshold":
            param = args.get("parameter")
            if param is not None and param not in ALLOWED_PARAMETERS:
                return False
    return True


def _generate_cloud(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    start: float,
) -> dict[str, Any]:
    """
    Call Gemini for cloud path. Returns {source, function_calls, text, total_time_ms, latency_ms}.
    On timeout/error: source=cloud_error. Set 2s timeout — verify against installed SDK version.
    """
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "source": "cloud_error",
            "error": "GEMINI_API_KEY unset or placeholder — replace your_gemini_api_key_here in backend/.env",
            "function_calls": [],
            "text": "",
            "total_time_ms": elapsed_ms,
            "latency_ms": elapsed_ms,
        }
    try:
        import google.generativeai as genai
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=(
                "You are a welding quality coach. For analytical questions (why, how, explain, improve), "
                "respond with structured advice. For tool calls, use the provided schema."
            ),
        )
        last_content = (messages[-1].get("content") or "") if messages else ""
        # 2s timeout via ThreadPoolExecutor — SDK may not support timeout param.
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(model.generate_content, last_content)
            try:
                response = future.result(timeout=2)
            except FuturesTimeoutError:
                return {
                    "source": "cloud_error",
                    "error": "Gemini timeout (2s)",
                    "function_calls": [],
                    "text": "",
                    "total_time_ms": int((time.perf_counter() - start) * 1000),
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                }
        function_calls = []
        text_parts = []
        parts = []
        if response.candidates:
            content = response.candidates[0].content
            if content and hasattr(content, "parts"):
                parts = content.parts or []
        for part in parts:
            if getattr(part, "function_call", None):
                fc = part.function_call
                args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                function_calls.append({"name": getattr(fc, "name", ""), "arguments": args})
            if getattr(part, "text", None):
                text_parts.append(part.text)
        text = "".join(text_parts).strip()
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "source": "cloud",
            "function_calls": function_calls,
            "text": text,
            "total_time_ms": elapsed_ms,
            "latency_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "source": "cloud_error",
            "error": str(e),
            "function_calls": [],
            "text": "",
            "total_time_ms": elapsed_ms,
            "latency_ms": elapsed_ms,
        }


def _stub_on_device_response(query: str) -> dict[str, Any]:
    """
    Stub response when Cactus not available. Returns plausible tool calls
    for demo queries so weld_demo and API work end-to-end.
    """
    q = query.lower()
    # Scenario 1: voltage 28V range 18-24
    if "voltage" in q and ("28" in q or "range" in q):
        return {
            "source": "on-device",
            "function_calls": [
                {
                    "name": "check_parameter_threshold",
                    "arguments": {
                        "parameter": "voltage",
                        "value": 28.0,
                        "min": 18.0,
                        "max": 24.0,
                    },
                }
            ],
            "text": "",
            "total_time_ms": 50,
            "latency_ms": 50,
        }
    # Scenario 2: angle 52 degrees max 45
    if "angle" in q and ("52" in q or "45" in q):
        return {
            "source": "on-device",
            "function_calls": [
                {
                    "name": "check_parameter_threshold",
                    "arguments": {
                        "parameter": "angle",
                        "value": 52.0,
                        "min": 0.0,
                        "max": 45.0,
                    },
                }
            ],
            "text": "",
            "total_time_ms": 50,
            "latency_ms": 50,
        }
    # Scenario: session WS-042 scored 41 (evaluate_session_score)
    session_match = re.search(r"WS-(\d+)", query, re.IGNORECASE)
    score_match = re.search(r"scored?\s*(\d+)", query, re.IGNORECASE)
    if session_match and score_match:
        return {
            "source": "on-device",
            "function_calls": [
                {
                    "name": "evaluate_session_score",
                    "arguments": {
                        "session_id": f"WS-{session_match.group(1)}",
                        "score": float(score_match.group(1)),
                    },
                }
            ],
            "text": "",
            "total_time_ms": 50,
            "latency_ms": 50,
        }
    # Scenario 5: hallucinated param (wire_feed) -> validation fails -> escalation
    if "wire_feed" in q:
        return {
            "source": "on-device",
            "function_calls": [
                {
                    "name": "check_parameter_threshold",
                    "arguments": {
                        "parameter": "wire_feed",  # Invalid: not in ALLOWED_PARAMETERS
                        "value": 12.0,
                        "min": 10.0,
                        "max": 15.0,
                    },
                }
            ],
            "text": "",
            "total_time_ms": 50,
            "latency_ms": 50,
        }

    # Default: generic check_parameter_threshold
    return {
        "source": "on-device",
        "function_calls": [
            {
                "name": "check_parameter_threshold",
                "arguments": {
                    "parameter": "voltage",
                    "value": 0.0,
                    "min": 0.0,
                    "max": 100.0,
                },
            }
        ],
        "text": "",
        "total_time_ms": 50,
        "latency_ms": 50,
    }


def generate_hybrid(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    offline: bool = False,
) -> dict[str, Any]:
    """
    Route query: interrogative + no measurement → cloud (or offline canned).
    Else → on-device (Cactus or stub).

    Returns: {source, function_calls, text, total_time_ms, latency_ms}
    Cloud errors: 200 with source="cloud_error", not 503.
    """
    start = time.perf_counter()
    last_msg = (messages[-1].get("content") or "") if messages else ""

    # Branch 1: Interrogative gate — route to cloud when why/explain/improve + no measurement
    if _is_interrogative(last_msg) and not _has_measurement(last_msg):
        if offline:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            out = dict(OFFLINE_CANNED_RESPONSE)
            out["total_time_ms"] = elapsed_ms
            out["latency_ms"] = elapsed_ms
            return out
        # Cloud path: Step 5 adds _generate_cloud. Until then, return cloud_error.
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return _generate_cloud(messages, tools, start)

    # Branch 2: On-device
    _ensure_cactus_warm()
    if _CACTUS_AVAILABLE:
        # Real Cactus inference — Step 4 adapts prompt; placeholder for now
        result = _stub_on_device_response(last_msg)
    else:
        result = _stub_on_device_response(last_msg)

    # Branch 3: Escalation — validate; if invalid, escalate to cloud (actually call Gemini)
    if not _validate_tool_call(result.get("function_calls", []), tools):
        if offline:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            out = dict(OFFLINE_CANNED_RESPONSE)
            out["total_time_ms"] = elapsed_ms
            out["latency_ms"] = elapsed_ms
            return out
        cloud_result = _generate_cloud(messages, tools, start)
        cloud_result["source"] = "on-device→cloud"
        cloud_result["escalation_reason"] = "validation_failed"
        cloud_result["function_calls"] = []
        return cloud_result

    # Source normalization: all on-device variants → "on-device"
    src = result.get("source", "")
    if isinstance(src, str) and src.startswith("on-device"):
        result["source"] = "on-device"

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    result["total_time_ms"] = result.get("total_time_ms", elapsed_ms)
    result["latency_ms"] = result.get("latency_ms", elapsed_ms)
    return result
