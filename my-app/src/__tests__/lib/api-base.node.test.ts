/** @jest-environment node */

import { getApiBase } from "@/lib/api-base";

describe("getApiBase (Node)", () => {
  it("returns empty string when run in Node (no window)", () => {
    expect(typeof window).toBe("undefined");
    expect(getApiBase()).toBe("");
  });
});
