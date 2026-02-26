/**
 * ExcursionLogTable tests.
 *
 * Verifies:
 * - Default sort by timestamp asc: reverse-ordered data → first row shows 1:40
 * - Empty state shows "No excursions"
 */

import { render, screen } from "@testing-library/react";
import { ExcursionLogTable } from "@/components/welding/ExcursionLogTable";
import type { ExcursionEntry } from "@/types/report-summary";

describe("ExcursionLogTable", () => {
  it("sorts by timestamp asc by default — first row shows 1:40 when data is reverse-ordered", () => {
    const excursions: ExcursionEntry[] = [
      {
        timestamp_ms: 200000,
        defect_type: "b",
        parameter_value: 1,
        threshold_value: 2,
        source: "frame_derived",
      },
      {
        timestamp_ms: 100000,
        defect_type: "a",
        parameter_value: 1,
        threshold_value: 2,
        source: "frame_derived",
      },
    ];

    render(<ExcursionLogTable excursions={excursions} />);

    expect(screen.getByText("1:40")).toBeInTheDocument();
    expect(screen.getByText("3:20")).toBeInTheDocument();

    // With default sort asc by timestamp, 100000ms (1:40) appears before 200000ms (3:20)
    const bodyText = document.body.textContent ?? "";
    const idx140 = bodyText.indexOf("1:40");
    const idx320 = bodyText.indexOf("3:20");
    expect(idx140).toBeGreaterThanOrEqual(0);
    expect(idx320).toBeGreaterThanOrEqual(0);
    expect(idx140).toBeLessThan(idx320);
  });

  it("shows empty state when excursions is empty", () => {
    render(<ExcursionLogTable excursions={[]} />);
    expect(screen.getByText(/No excursions/i)).toBeInTheDocument();
  });
});
