/**
 * GET /api/warp/welders/[welderId]/quality-trend
 * Proxies to backend GET /api/welders/{welder_id}/quality-trend.
 * Next.js 16: params is a Promise — await before use.
 */
import { NextResponse } from "next/server";
import type { WelderTrendPoint } from "@/types/warp-analysis";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ welderId: string }> },
): Promise<NextResponse<WelderTrendPoint[] | { detail: string }>> {
  const { welderId } = await params;
  try {
    const res = await fetch(
      `${API_BASE}/api/welders/${encodeURIComponent(welderId)}/quality-trend`,
    );
    const text = await res.text();
    let data: unknown;
    try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 200) }; }
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
