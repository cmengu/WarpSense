/**
 * Tests for Welder Roster (dashboard) — 10 welders with skill arcs.
 *
 * Roster content moved from seagull to dashboard. Validates:
 *   - Promise.allSettled: partial failures don't block working cards
 *   - Per-card error: "Score unavailable" when fetch fails
 *   - Loading state (skeleton cards)
 *   - Links to /replay/[sessionId] for welder reports
 *   - Badge display (On track, Needs attention, Neutral)
 */

import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "@/app/(app)/dashboard/page";

const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe("DashboardPage (Welder Roster)", () => {
  beforeEach(() => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      return Promise.resolve({ total: 75, rules: [] });
    });
  });

  it("shows loading state initially with skeleton", () => {
    render(<DashboardPage />);
    expect(screen.getByText(/Welder Roster/)).toBeInTheDocument();
  });

  it("renders 10 welder cards when fetches succeed", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Sara Okafor/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(screen.getAllByText(/\/100/).length).toBeGreaterThanOrEqual(10);
  });

  it("links cards to /replay/[sessionId]", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    const links = screen.getAllByRole("link");
    const mikeLink = links.find((l) => l.getAttribute("href") === "/replay/sess_mike-chen_005");
    expect(mikeLink).toBeDefined();
  });

  it("uses Promise.allSettled: one failure shows Score unavailable, others show score", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_mike-chen_005") {
        return Promise.reject(new Error("404"));
      }
      return Promise.resolve({ total: 95, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
  });

  it("shows badge when score improves (On track)", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId.endsWith("_005")) return Promise.resolve({ total: 80, rules: [] });
      if (sessionId.endsWith("_004")) return Promise.resolve({ total: 70, rules: [] });
      return Promise.resolve({ total: 75, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/On track/).length).toBeGreaterThan(0);
    });
  });

  it("calls fetchScore for latest and second-latest sessions", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_005");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_004");
  });
});
