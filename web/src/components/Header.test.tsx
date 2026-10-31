import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Header } from "./Header";

const flows = [
  { id: "checkout", name: "Checkout page", start_url: "/store/checkout.html", goal: "Pay", pages: ["checkout.html"], single_page: true },
  { id: "purchase", name: "Purchase flow", start_url: "/store/product.html", goal: "Buy", pages: ["product.html", "cart.html", "checkout.html", "confirm.html"], single_page: false },
];

describe("Header flow picker", () => {
  it("lets the user pick the flow and reports the choice", () => {
    const onFlowChange = vi.fn();
    render(<Header flows={flows} flowId="purchase" run={null} mode="replay" canLive={false} running={false} onModeChange={() => {}} onRun={() => {}} onFlowChange={onFlowChange} />);
    const select = screen.getByRole("combobox", { name: /flow/i });
    expect(select).toHaveValue("purchase");
    fireEvent.change(select, { target: { value: "checkout" } });
    expect(onFlowChange).toHaveBeenCalledWith("checkout");
  });
});
