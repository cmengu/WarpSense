/** @jest-environment jsdom */

import { getApiBase } from "@/lib/api-base";

describe("getApiBase (jsdom)", () => {
  const origEnv = process.env;

  afterEach(() => {
    process.env = { ...origEnv };
  });

  it("returns base path when NEXT_PUBLIC_BASE_PATH set", () => {
    (process.env as { NEXT_PUBLIC_BASE_PATH?: string }).NEXT_PUBLIC_BASE_PATH =
      "/weldingsense";
    expect(getApiBase()).toBe("/weldingsense");
  });

  it("strips trailing slash when base path set", () => {
    (process.env as { NEXT_PUBLIC_BASE_PATH?: string }).NEXT_PUBLIC_BASE_PATH =
      "/weldingsense/";
    expect(getApiBase()).toBe("/weldingsense");
  });

  it("returns empty string when NEXT_PUBLIC_BASE_PATH unset", () => {
    delete (process.env as { NEXT_PUBLIC_BASE_PATH?: string })
      .NEXT_PUBLIC_BASE_PATH;
    expect(getApiBase()).toBe("");
  });
});
