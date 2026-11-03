import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UrlRun } from "./UrlRun";

const W3C = "https://www.w3.org/WAI/demos/bad/before/home.html";
const base = { suggested: [W3C, "https://a.example/"], closed: false, running: false, refusal: null, onRun: () => {} };

describe("UrlRun (Task 26F.6)", () => {
  it("consent gates the button: nothing starts until the visitor affirms the page is public and theirs to audit", () => {
    const onRun = vi.fn();
    render(<UrlRun {...base} onRun={onRun} />);
    const field = screen.getByRole("textbox", { name: /page address/i });
    const button = screen.getByRole("button", { name: /audit this page/i });
    expect(button).toBeDisabled();
    fireEvent.change(field, { target: { value: W3C } });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i }));
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(onRun).toHaveBeenCalledWith({ url: W3C, screens: 1, consent: true, hint: "" });
  });

  it("sends the screens choice and the hint, and fills the field from a suggested page", () => {
    const onRun = vi.fn();
    render(<UrlRun {...base} onRun={onRun} />);
    fireEvent.click(screen.getByRole("button", { name: /www\.w3\.org/ }));  // a suggested page fills the field
    expect(screen.getByRole("textbox", { name: /page address/i })).toHaveValue(W3C);
    fireEvent.click(screen.getByRole("radio", { name: /up to three screens/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /what the page is about/i }), { target: { value: "a demo shop" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i }));
    fireEvent.click(screen.getByRole("button", { name: /audit this page/i }));
    expect(onRun).toHaveBeenCalledWith({ url: W3C, screens: 3, consent: true, hint: "a demo shop" });
    expect(screen.getByRole("textbox", { name: /what the page is about/i })).toHaveAttribute("maxlength", "120");
  });

  it("shows a refusal verbatim, as an alert, and keeps the field for a second try", () => {
    render(<UrlRun {...base} refusal="This address is not public." />);
    expect(screen.getByRole("alert")).toHaveTextContent("This address is not public.");
    expect(screen.getByRole("textbox", { name: /page address/i })).toBeEnabled();
  });

  it("says when the field is closed for today and offers nothing to click", () => {
    render(<UrlRun {...base} closed />);
    expect(screen.getByRole("status")).toHaveTextContent(/closed for today/i);
    expect(screen.getByRole("button", { name: /audit this page/i })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: /page address/i })).toBeDisabled();
  });

  it("links the policy page and sets expectations in one line", () => {
    render(<UrlRun {...base} />);
    expect(screen.getByRole("link", { name: /what Parity does on your page/i })).toHaveAttribute("href", "/audit-policy");
    expect(screen.getByText(/Read-only\. Sites behind bot challenges or logins end the run early, and we say so\./)).toBeInTheDocument();
  });

  it("offers the W3C demo page when no suggested page is configured", () => {
    render(<UrlRun {...base} suggested={[]} />);
    expect(screen.getByRole("button", { name: /www\.w3\.org/ })).toBeInTheDocument();
  });
});

describe("QA gate before the 6c merge: the panel keeps focus and keeps out of the way", () => {
  it("keeps the submit button in the tab ring while the run is going: aria-disabled, not disabled, and a click starts nothing", () => {
    const onRun = vi.fn();
    render(<UrlRun {...base} running onRun={onRun} />);
    const button = screen.getByRole("button", { name: /auditing/i });
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(button);
    expect(onRun).not.toHaveBeenCalled();
  });

  it("moves focus to the address field when the server refuses, so the retry is one keystroke away", () => {
    const { rerender } = render(<UrlRun {...base} />);
    rerender(<UrlRun {...base} refusal="This address is not public." />);
    expect(screen.getByRole("textbox", { name: /page address/i })).toHaveFocus();
  });

  it("folds to one line once its run is on screen, and unfolds with the field focused for another page", () => {
    render(<UrlRun {...base} active="developer.mozilla.org" />);
    expect(screen.queryByRole("textbox", { name: /page address/i })).toBeNull();
    expect(screen.getByText(/developer\.mozilla\.org/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /audit another page/i }));
    expect(screen.getByRole("textbox", { name: /page address/i })).toHaveFocus();
  });

  it("accepts an address typed without a scheme and sends it as https", () => {
    const onRun = vi.fn();
    render(<UrlRun {...base} onRun={onRun} />);
    fireEvent.change(screen.getByRole("textbox", { name: /page address/i }), { target: { value: "www.w3.org/WAI/demos/bad/before/home.html" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /public and I may audit it/i }));
    fireEvent.click(screen.getByRole("button", { name: /audit this page/i }));
    expect(onRun).toHaveBeenCalledWith({ url: W3C, screens: 1, consent: true, hint: "" });
  });

  it("names suggested pages by host and path when the host repeats, and focuses the field after filling it", () => {
    render(<UrlRun {...base} suggested={["https://a.example/one", "https://a.example/two"]} />);
    fireEvent.click(screen.getByRole("button", { name: "a.example/two" }));
    expect(screen.getByRole("textbox", { name: /page address/i })).toHaveFocus();
    expect(screen.getByRole("textbox", { name: /page address/i })).toHaveValue("https://a.example/two");
  });

  it("opens the policy page in a new tab and says so, so a half-typed address is not lost", () => {
    render(<UrlRun {...base} />);
    const link = screen.getByRole("link", { name: /what Parity does on your page.*new tab/i });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringMatching(/noopener/));
  });
});
