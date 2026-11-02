import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import hero from "../fixtures/hero.json";
import { ScreenReaderPanel } from "./ScreenReaderPanel";
import type { Finding } from "../state/types";

const finding = (hero as unknown as { findings: Finding[] }).findings[0];

describe("ScreenReaderPanel reads in the order a judge needs", () => {
  it("shows what is on screen first and what is announced second, at the same size", () => {
    render(<ScreenReaderPanel finding={finding} />);
    const seen = screen.getByText("On screen");
    const heard = screen.getByText("Announced");
    expect(seen.compareDocumentPosition(heard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(seen.nextElementSibling?.className).toContain("sr-pair");
    expect(heard.nextElementSibling?.className).toContain("sr-pair");
  });
  it("does not say the same thing twice when the judge's impact line exists", () => {
    render(<ScreenReaderPanel finding={{ ...finding, why_it_matters: "Blind user cannot confirm the payment.", judgement: { ...finding.judgement!, impact: "User hears only Submit." } }} />);
    expect(screen.queryByText("Blind user cannot confirm the payment.")).toBeNull();
    expect(screen.getByText("User hears only Submit.")).toBeInTheDocument();
  });
});
