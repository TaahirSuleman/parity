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

describe("ScreenReaderPanel Voice (P6)", () => {
  const voiced: Finding = { ...finding, voice: { clip_key: "checkout.wav", start_ms: 7200, end_ms: 10000, transcript: "Submit, button", agrees: true } };
  it("plays the segment, shows the transcript with the Voice Transcribe badge and the agreement, and names Voice primary evidence at the gate", () => {
    render(<ScreenReaderPanel finding={voiced} voiceAccuracy={0.93} />);
    expect(document.querySelector("audio")?.getAttribute("src")).toBe("/store/voice/checkout.wav#t=7.2,10");
    expect(screen.getByText("Submit, button")).toBeInTheDocument();
    expect(screen.getByText(/MUSE VOICE TRANSCRIBE/)).toBeInTheDocument();
    expect(screen.getByText(/transcript agrees with the accessibility tree/i)).toBeInTheDocument();
    expect(screen.getByText(/primary evidence/i)).toHaveTextContent("93%");
  });
  it("names Voice corroboration below the gate, with the measured accuracy", () => {
    render(<ScreenReaderPanel finding={voiced} voiceAccuracy={0.71} />);
    expect(screen.getByText(/corroboration/i)).toHaveTextContent("71%");
    expect(screen.queryByText(/primary evidence/i)).toBeNull();
  });
  it("says when the transcript does not agree, and says nothing about Voice when the page has no clip", () => {
    const first = render(<ScreenReaderPanel finding={{ ...voiced, voice: { ...voiced.voice!, transcript: "Pay, button", agrees: false } }} voiceAccuracy={0.93} />);
    expect(screen.getByText(/transcript differs from the accessibility tree/i)).toBeInTheDocument();
    first.unmount();
    render(<ScreenReaderPanel finding={finding} />);
    expect(screen.queryByLabelText("VoiceOver evidence")).toBeNull();
    expect(document.querySelectorAll("audio")).toHaveLength(0);
  });
});
