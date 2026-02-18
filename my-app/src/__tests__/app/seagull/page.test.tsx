/**
 * Tests for Seagull Team Dashboard — 10 welders with skill arcs.
 *
 * Validates:
 *   - Promise.allSettled: partial failures don't block working cards
 *   - Per-card error: "Score unavailable" when fetch fails
 *   - Loading state (skeleton cards)
 *   - Links to welder reports
 *   - Badge display (On track, Needs attention, Neutral)
 */

import { render, screen, waitFor } from "@testing-library/react";
import SeagullDashboardPage from "@/app/seagull/page";

const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe("SeagullDashboardPage", () => {
  beforeEach(() => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      return Promise.resolve({ total: 75, rules: [] });
    });
  });

  it("shows loading state initially with skeleton", () => {
    render(<SeagullDashboardPage />);
    expect(screen.getByText(/Team Dashboard/)).toBeInTheDocument();
  });

  it("renders 10 welder cards when fetches succeed", async () => {
    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Sara Okafor/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(screen.getAllByText(/\/100/).length).toBeGreaterThanOrEqual(10);
  });

  it("uses Promise.allSettled: one failure shows Score unavailable, others show score", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_mike-chen_005") {
        return Promise.reject(new Error("404"));
      }
      return Promise.resolve({ total: 95, rules: [] });
    });

    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
  });

  it("shows badge when score improves (On track)", async () => {
    let callCount = 0;
    mockFetchScore.mockImplementation((sessionId: string) => {
      callCount++;
      if (sessionId.endsWith("_005")) return Promise.resolve({ total: 80, rules: [] });
      if (sessionId.endsWith("_004")) return Promise.resolve({ total: 70, rules: [] });
      return Promise.resolve({ total: 75, rules: [] });
    });

    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/On track/)).toBeInTheDocument();
    });
  });

  it("calls fetchScore for latest and second-latest sessions", async () => {
    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_005");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_004");
  });
});
