/**
 * GET /api/warp/simulator/closest-match
 * Proxies to FastAPI GET /api/simulator/closest-match
 */
import { NextResponse } from "next/server";
import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

const API_BASE = getServerBackendBaseUrl();
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams({
      heat_input_level: searchParams.get("heat_input_level") ?? "",
      torch_angle_deviation: searchParams.get("torch_angle_deviation") ?? "",
      arc_stability: searchParams.get("arc_stability") ?? "",
    });
    const res = await fetch(`${API_BASE}/api/simulator/closest-match?${params}`, {
      method: "GET",
    });
    const text = await res.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text.slice(0, 200) };
    }
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
