import { describe, expect, it } from "vitest";
import { ApiError } from "../api";
import { startRunMessage } from "./errors";

describe("startRunMessage", () => {
  it("turns a 429 into when to retry and the way in (Replay), not a failed run", () => {
    const err = new ApiError(429, "a Live run is already in progress", { error: "a Live run is already in progress", retry_after_s: 60, suggestion: "replay" });
    const m = startRunMessage(err);
    expect(m.kind).toBe("notice");
    expect(m.text).toMatch(/already in progress/);
    expect(m.text).toMatch(/60 s/);
    expect(m.text).toMatch(/Replay/);
  });
  it("keeps a missing key or a disabled Live as a plain explanation", () => {
    expect(startRunMessage(new ApiError(503, "Live mode needs MODEL_API_KEY on the server; use Replay")).text).toMatch(/MODEL_API_KEY/);
    expect(startRunMessage(new Error("Failed to fetch")).kind).toBe("error");
  });
});
