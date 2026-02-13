/**
 * Centralized logging utility.
 *
 * - Development: logs to console; production: silent for non-alerts.
 * - Replay load failures trigger an immediate alert (webhook) for monitoring.
 *
 * Configure NEXT_PUBLIC_ALERT_WEBHOOK_URL to receive alerts (e.g. Slack, PagerDuty).
 * Alerts are always sent regardless of NODE_ENV when the webhook is set.
 */

const isDev = process.env.NODE_ENV === "development";
const ALERT_WEBHOOK_URL = process.env.NEXT_PUBLIC_ALERT_WEBHOOK_URL?.trim() || "";

export function logError(
  context: string,
  error: unknown,
  additionalInfo?: Record<string, unknown>
): void {
  if (isDev) {
    console.error(`[${context}]`, error, additionalInfo ?? "");
  }
}

export function logWarn(
  context: string,
  message: string,
  additionalInfo?: Record<string, unknown>
): void {
  if (isDev) {
    console.warn(`[${context}]`, message, additionalInfo ?? "");
  }
}

/**
 * Log and alert when a replay fails to load.
 * Use this so you get immediate notification when a user hits a broken replay.
 *
 * Alerts are sent via POST to NEXT_PUBLIC_ALERT_WEBHOOK_URL when configured.
 * Fire-and-forget — does not block the UI.
 */
export function alertOnReplayFailure(
  sessionId: string,
  error: unknown,
  additionalInfo?: Record<string, unknown>
): void {
  const errMessage =
    error instanceof Error ? error.message : String(error);
  const payload = {
    event: "replay_load_failed",
    sessionId,
    error: errMessage,
    timestamp: new Date().toISOString(),
    ...additionalInfo,
  };

  // Always log in dev
  if (isDev) {
    console.error("[ReplayLoadFailed]", payload);
  }

  // Send alert webhook if configured
  if (ALERT_WEBHOOK_URL) {
    fetch(ALERT_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch((fetchErr) => {
      if (isDev) {
        console.error("[Logger] Alert webhook failed:", fetchErr);
      }
    });
  }
}
