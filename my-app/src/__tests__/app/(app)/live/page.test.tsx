/**
 * Live page — iPad companion PWA smoke test.
 * Verifies WarpSense Live page renders without WebGL, polls warp-risk.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import LivePage from "@/app/(app)/live/page";

const mockFetchWarpRisk = jest.fn();

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => (key === "session" ? null : null),
  }),
}));

jest.mock("@/lib/api", () => ({
  fetchWarpRisk: (...args: unknown[]) => mockFetchWarpRisk(...args),
}));

describe("LivePage", () => {
  beforeEach(() => {
    mockFetchWarpRisk.mockResolvedValue({
      session_id: "sess_novice_001",
      probability: 0.15,
      risk_level: "ok",
      model_available: true,
      window_frames_used: 50,
    });
  });

  it("renders WarpSense Live heading", async () => {
    render(<LivePage />);
    await waitFor(() => {
      expect(screen.getByText("WarpSense Live")).toBeInTheDocument();
    });
  });

  it("renders NOMINAL status when risk is ok", async () => {
    render(<LivePage />);
    await waitFor(() => {
      expect(screen.getByText("NOMINAL")).toBeInTheDocument();
    });
  });

  it("renders warp risk percentage from API", async () => {
    render(<LivePage />);
    await waitFor(() => {
      expect(screen.getByText("15%")).toBeInTheDocument();
    });
  });

  it("calls fetchWarpRisk with default session when no query param", async () => {
    render(<LivePage />);
    await waitFor(() => {
      expect(mockFetchWarpRisk).toHaveBeenCalledWith("sess_novice_001");
    });
  });

  it("Dismiss button has min 48px touch target", async () => {
    mockFetchWarpRisk.mockResolvedValue({
      session_id: "sess_novice_001",
      probability: 0.6,
      risk_level: "warning",
      model_available: true,
      window_frames_used: 50,
    });
    render(<LivePage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Dismiss/i })).toBeInTheDocument();
    });
    const btn = screen.getByRole("button", { name: /Dismiss/i });
    expect(btn).toHaveClass("min-h-[48px]");
  });
});
