/**
 * GET /api/warp/sessions/[sessionId]/reports
 * Next.js 16: params is a Promise — await before use.
 */
import { NextResponse } from "next/server";
import type { WarpReport } from "@/types/warp-analysis";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const dynamic = "force-dynamic";
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
): Promise<NextResponse<WarpReport | { detail: string }>> {
  const { sessionId } = await params;
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/reports`);
    const text = await res.text();
    let data: unknown;
    try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 200) }; }
    return NextResponse.json(
      data as WarpReport | { detail: string },
      { status: res.status },
    );
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
