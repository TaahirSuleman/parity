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
