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

describe("run links by path (stress pass)", () => {
  it("also reads /runs/<id>, the form the server and the QA report call a run link", async () => {
    const { runIdFromLocation } = await import("./location");
    expect(runIdFromLocation("/runs/20261031-1234-ab", "")).toBe("20261031-1234-ab");
    expect(runIdFromLocation("/", "?run=r1")).toBe("r1");
    expect(runIdFromLocation("/runs/..%2Fetc", "")).toBeNull();
    expect(runIdFromLocation("/eval", "")).toBeNull();
  });
});
