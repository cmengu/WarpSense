import {
  computeHistoricalScores,
  getTrajectoryFromResults,
  assertTrajectoryAtIdx,
  HIST_FIRST_IDX,
} from "@/lib/welder-report-utils";
import { __FETCH_ORDER_FOR_TEST } from "@/app/seagull/welder/[id]/page";

describe("welder-report-utils", () => {
  it("computeHistoricalScores returns number[] and excludes trajectory", () => {
    const histCount = 3;
    const trajectoryIdx = HIST_FIRST_IDX + histCount;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: 70, rules: [] } },
      { status: "fulfilled" as const, value: { total: 72, rules: [] } },
      { status: "fulfilled" as const, value: { total: 74, rules: [] } },
      { status: "fulfilled" as const, value: { welder_id: "x", points: [] } },
    ];
    const historicalScores = computeHistoricalScores(mockResults, trajectoryIdx);
    expect(historicalScores).toEqual([70, 72, 74]);
  });

  it("computeHistoricalScores throws when value is NaN", () => {
    const trajectoryIdx = HIST_FIRST_IDX + 1;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: NaN, rules: [] } },
      { status: "fulfilled" as const, value: { welder_id: "x", points: [] } },
    ];
    expect(() =>
      computeHistoricalScores(mockResults, trajectoryIdx)
    ).toThrow(/historicalScores must be finite number/);
  });

  it("computeHistoricalScores throws when trajectory leaks into histResults", () => {
    const trajectoryIdx = HIST_FIRST_IDX + 1;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { welder_id: "leak", points: [] } },
      { status: "fulfilled" as const, value: { welder_id: "x", points: [] } },
    ];
    expect(() =>
      computeHistoricalScores(mockResults, trajectoryIdx)
    ).toThrow(/historicalScores must be finite number/);
  });

  it("contract: HIST_FIRST_IDX matches page allPromises layout", () => {
    const firstHistIdx = __FETCH_ORDER_FOR_TEST.indexOf("hist");
    expect(HIST_FIRST_IDX).toBe(firstHistIdx);
    expect(HIST_FIRST_IDX).toBe(3);
  });

  it("contract: trajectoryIdx derived from HIST_FIRST_IDX yields correct historicalScores length", () => {
    const histCount = 5;
    const trajectoryIdx = HIST_FIRST_IDX + histCount;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      ...Array.from({ length: histCount }, (_, i) => ({
        status: "fulfilled" as const,
        value: { total: 70 + i * 2, rules: [] },
      })),
      { status: "fulfilled" as const, value: { welder_id: "x", points: [] } },
    ];
    const historicalScores = computeHistoricalScores(mockResults, trajectoryIdx);
    expect(historicalScores.length).toBe(histCount);
  });

  it("assertTrajectoryAtIdx throws when result at trajectoryIdx is SessionScore not WelderTrajectory", () => {
    const trajectoryIdx = 4;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: 70, rules: [] } },
      { status: "fulfilled" as const, value: { total: 72, rules: [] } },
    ];
    expect(() => assertTrajectoryAtIdx(mockResults, trajectoryIdx)).toThrow(
      /trajectory invariant violated|welder_id/
    );
  });

  it("assertTrajectoryAtIdx does not throw when last result has welder_id", () => {
    const trajectoryIdx = 4;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: 70, rules: [] } },
      { status: "fulfilled" as const, value: { welder_id: "mike-chen", points: [] } },
    ];
    expect(() => assertTrajectoryAtIdx(mockResults, trajectoryIdx)).not.toThrow();
  });

  it("getTrajectoryFromResults returns trajectory when fulfilled", () => {
    const trajectoryIdx = 4;
    const traj = { welder_id: "mike-chen", points: [], trend_slope: 2, projected_next_score: 82 };
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: 70, rules: [] } },
      { status: "fulfilled" as const, value: traj },
    ];
    expect(getTrajectoryFromResults(mockResults, trajectoryIdx)).toEqual(traj);
  });

  it("getTrajectoryFromResults returns null when rejected", () => {
    const trajectoryIdx = 4;
    const mockResults = [
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: {} },
      { status: "fulfilled" as const, value: { total: 75, rules: [] } },
      { status: "fulfilled" as const, value: { total: 70, rules: [] } },
      { status: "rejected" as const, reason: new Error("Network error") },
    ];
    expect(getTrajectoryFromResults(mockResults, trajectoryIdx)).toBeNull();
  });
});
