/** GET /api/warp/mock-sessions — proxy to FastAPI GET /api/mock-sessions. */
import { NextResponse } from "next/server";
import type { MockSession } from "@/types/warp-analysis";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const dynamic = "force-dynamic";
export async function GET(): Promise<NextResponse<MockSession[] | { detail: string }>> {
  try {
    const res = await fetch(`${API_BASE}/api/mock-sessions`);
    const text = await res.text();
    let data: unknown;
    try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 200) }; }
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
