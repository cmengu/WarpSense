"""
Prompt version registry.

Every LLM call logs its prompt version via structured logging.
Changing a prompt = new version string here, not overwriting.
Eval output reports which version produced which score.

Keys MUST match the string returned by each agent's agent_name property:
  ThermalAgent.agent_name          -> "ThermalAgent"
  GeometryAgent.agent_name         -> "GeometryAgent"
  ProcessStabilityAgent.agent_name -> "ProcessStabilityAgent"
  WarpSenseAgent (step 4 method)   -> "WarpSenseAgent"
"""

PROMPT_VERSIONS: dict[str, str] = {
    "ThermalAgent":           "thermal_v1",
    "GeometryAgent":          "geometry_v1",
    "ProcessStabilityAgent":  "process_v1",
    "WarpSenseAgent":         "single_agent_v1",
}
