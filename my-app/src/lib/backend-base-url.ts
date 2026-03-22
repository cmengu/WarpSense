/**
 * Normalized FastAPI origin for browser and server (NEXT_PUBLIC_API_URL).
 * Coerces https://localhost → http://localhost — uvicorn dev is HTTP-only.
 */
const DEFAULT_BACKEND = "http://localhost:8000";

export function getBackendBaseUrl(): string {
  const raw =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL?.trim()) ||
    DEFAULT_BACKEND;
  try {
    const u = new URL(raw);
    const isLocal =
      u.hostname === "localhost" ||
      u.hostname === "127.0.0.1" ||
      u.hostname === "[::1]";
    if (isLocal && u.protocol === "https:") {
      u.protocol = "http:";
      return u.origin;
    }
    return u.origin;
  } catch {
    return DEFAULT_BACKEND;
  }
}
