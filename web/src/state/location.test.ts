import { describe, expect, it } from "vitest";
import { runIdFromSearch, withRunParam } from "./location";

describe("run links", () => {
  it("reads and writes ?run=<id> so a run can be reloaded and shared", () => {
    expect(runIdFromSearch("?run=20261031-1234-ab")).toBe("20261031-1234-ab");
    expect(runIdFromSearch("?mock=hero")).toBeNull();
    expect(runIdFromSearch("?run=../etc")).toBeNull(); // only run ids
    expect(withRunParam("?mock=hero", "r1")).toBe("?mock=hero&run=r1");
    expect(withRunParam("?run=old", "r2")).toBe("?run=r2");
    expect(withRunParam("?run=old", null)).toBe("");
  });
});
