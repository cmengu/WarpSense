/** GET /api/warp/health — proxy to FastAPI GET /api/health/warp. */
import { NextResponse } from "next/server";
import type { WarpHealthResponse } from "@/types/warp-analysis";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const dynamic = "force-dynamic";
export async function GET(): Promise<NextResponse<WarpHealthResponse>> {
  try {
    const res = await fetch(`${API_BASE}/api/health/warp`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ graph_initialised: false, classifier_initialised: false }, { status: 200 });
  }
}
