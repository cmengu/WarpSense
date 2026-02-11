/**
 * Minimal logging utility with context.
 * In development: logs to console. In production: silent (errors still surface via UI).
 */

const isDev = process.env.NODE_ENV === "development";

export function logError(
  context: string,
  error: unknown,
  additionalInfo?: Record<string, unknown>
): void {
  if (isDev) {
    console.error(`[${context}]`, error, additionalInfo ?? "");
  }
}
