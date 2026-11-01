import { describe, expect, it } from "vitest";
import { ApiError } from "../api";
import { startRunMessage } from "./errors";

describe("startRunMessage", () => {
  it("turns a per-visitor 429 into one sentence: the limit, when to retry in human units, and the Replay way in", () => {
    const body = { error: "you have used this hour's Live runs", retry_after_s: 3598, suggestion: "replay", detail: "you have used this hour's Live runs" };
    const m = startRunMessage(new ApiError(429, body.detail, body));
    expect(m.kind).toBe("notice");
    expect(m.text).toMatch(/used this hour's Live runs/);
    expect(m.text).toMatch(/about 60 min/);
    expect((m.text.match(/Replay/g) ?? []).length).toBe(1);
    expect((m.text.match(/[Tt]ry again/g) ?? []).length).toBe(1);
  });
  it("says hours for the daily limit and seconds for the slot", () => {
    expect(startRunMessage(new ApiError(429, "x", { error: "today's Live runs are used up for everyone", retry_after_s: 86399 })).text).toMatch(/about 24 h/);
    expect(startRunMessage(new ApiError(429, "x", { error: "a Live run is already in progress", retry_after_s: 60 })).text).toMatch(/60 s/);
  });
  it("keeps a missing key or a disabled Live as a plain explanation", () => {
    expect(startRunMessage(new ApiError(503, "Live mode needs MODEL_API_KEY on the server; use Replay")).text).toMatch(/MODEL_API_KEY/);
    expect(startRunMessage(new Error("Failed to fetch")).kind).toBe("error");
  });
});
