/**
 * Base path for API requests when Next.js basePath is configured.
 *
 * Set NEXT_PUBLIC_BASE_PATH at build time to match next.config basePath.
 * Note: Next.js inlines NEXT_PUBLIC_* at build; unit test mutates process.env in Node
 * and may not reflect real browser behavior. See Known Issues.
 */
export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const base =
    (typeof process !== "undefined" &&
      (process.env as { NEXT_PUBLIC_BASE_PATH?: string })
        ?.NEXT_PUBLIC_BASE_PATH) ??
    "";
  return String(base).replace(/\/$/, "");
}
