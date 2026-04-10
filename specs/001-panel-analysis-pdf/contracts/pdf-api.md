# Contract: PDF Report Generation API

**Endpoint**: `POST /api/welder-report-pdf`
**Consumer**: `QualityReportCard.tsx` (via fetch)
**Provider**: `my-app/src/app/api/welder-report-pdf/route.ts`
**Version**: 2.0 (panel-centric)

---

## Request

**Content-Type**: `application/json`
**Content-Length**: required (chunked encoding rejected with 411)
**Max body size**: 5 MB

### Body Schema

```json
{
  "panel": {
    "id": "PANEL-A01",
    "name": "Deck Panel A-01"
  },
  "welder_attribution": "Ahmad Razif, Lee Wei",
  "score": {
    "total": 78,
    "rules": []
  },
  "disposition": "REWORK_REQUIRED",
  "rework_cost_usd": 1250.00,
  "sessionDate": "2026-03-25",
  "duration": "14m 32s",
  "station": "Station 3",
  "feedback": {
    "summary": "Heat profile exceeded WPS limits.",
    "feedback_items": [
      { "message": "Peak temperature exceeded by 12%", "severity": "high" }
    ]
  },
  "chartDataUrl": "data:image/png;base64,...",
  "narrative": "The weld showed consistent arc instability...",
  "reportSummary": { ... },
  "certifications": null,
  "agentInsights": [
    {
      "agent_name": "thermal_agent",
      "disposition": "REWORK_REQUIRED",
      "root_cause": "Heat input spiked to 2.4 kJ/mm at 4m12s, exceeding the WPS maximum of 1.8 kJ/mm.",
      "disposition_rationale": "The thermal excursion indicates insufficient travel speed control, placing the HAZ outside safe bounds.",
      "consequence": "Excessive heat input in the heat-affected zone can cause grain coarsening, reducing joint toughness and increasing the risk of HAZ cracking under load.",
      "reject_label": "HEAT EXCEEDANCE",
      "corrective_actions": [
        "Reduce travel speed to maintain heat input below 1.8 kJ/mm",
        "Verify pre-heat temperature before restarting"
      ]
    },
    {
      "agent_name": "geometry_agent",
      "disposition": "PASS",
      "root_cause": null,
      "disposition_rationale": null,
      "consequence": null,
      "reject_label": null,
      "corrective_actions": []
    },
    {
      "agent_name": "process_agent",
      "disposition": "PASS",
      "root_cause": null,
      "disposition_rationale": null,
      "consequence": null,
      "reject_label": null,
      "corrective_actions": []
    }
  ]
}
```

### Field Rules

| Field | Rule |
|---|---|
| `panel.id` | Required, non-empty string |
| `panel.name` | Required, non-empty string |
| `welder_attribution` | Optional; null or comma-separated names |
| `score.total` | Required; integer 0–100 |
| `disposition` | Optional; one of `"PASS"`, `"CONDITIONAL"`, `"REWORK_REQUIRED"` |
| `rework_cost_usd` | Optional; positive number or null |
| `chartDataUrl` | Optional; must start with `data:image/png`; max 2 MB |
| `narrative` | Optional; max 2000 characters |
| `agentInsights[n].agent_name` | Required per entry; one of `thermal_agent`, `geometry_agent`, `process_agent` |
| `agentInsights[n].root_cause` | Null if agent passed |
| `agentInsights[n].disposition_rationale` | Null if agent passed |
| `agentInsights[n].consequence` | Null if agent passed |
| `agentInsights[n].reject_label` | Null if agent passed; short uppercase label if rejected |

---

## Response

**Success (200)**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="PANEL-A01-warp-report.pdf"
```

Body: binary PDF buffer.

**Error Responses**

| Status | Condition |
|---|---|
| 400 | Invalid JSON, missing required fields, validation failure |
| 411 | Chunked transfer encoding without Content-Length |
| 413 | Body exceeds 5 MB |
| 500 | PDF render failure |

---

## Backward Compatibility

The legacy `welder` field (object with `name`) is removed. Any caller using the v1 contract must migrate to `panel` + `welder_attribution`. The PDF route will return 400 if `panel` is absent and `welder` is provided, to prevent silent fallback to v1 behaviour.
