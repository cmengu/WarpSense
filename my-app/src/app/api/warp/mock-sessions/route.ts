/** GET /api/warp/mock-sessions — proxy to FastAPI GET /api/mock-sessions. */
import { NextResponse } from "next/server";
import type { MockSession } from "@/types/warp-analysis";
import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

const API_BASE = getServerBackendBaseUrl();
export const dynamic = "force-dynamic";
export async function GET(): Promise<NextResponse<MockSession[] | { detail: string }>> {
  try {
    const res = await fetch(`${API_BASE}/api/mock-sessions`);
    const text = await res.text();
    let data: unknown;
    try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 200) }; }
    return NextResponse.json(
      data as MockSession[] | { detail: string },
      { status: res.status },
    );
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
