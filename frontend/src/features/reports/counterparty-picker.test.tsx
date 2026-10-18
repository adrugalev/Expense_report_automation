import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CounterpartyPicker } from "@/features/reports/counterparty-picker";

afterEach(cleanup);

function Harness({ enabled = true, onSelect = vi.fn() }: { enabled?: boolean; onSelect?: (value: string) => void }) {
  const [value, setValue] = useState("ПИК");
  const [open, setOpen] = useState(false);
  return <CounterpartyPicker value={value} options={enabled ? ["ПИК", "ANTTEQ", "MR Group"] : []}
    open={open} onOpenChange={setOpen} onChange={setValue} onSelect={onSelect} />;
}

describe("CounterpartyPicker", () => {
  it("keeps manual input before autofill has enabled company choices", async () => {
    const user = userEvent.setup();
    render(<Harness enabled={false} />);
    const input = screen.getByRole("textbox", { name: "Контрагент / организация" });
    await user.clear(input);
    await user.type(input, "Моя компания");
    expect(input).toHaveValue("Моя компания");
    expect(screen.queryByRole("button", { name: "Выбрать контрагента" })).not.toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows every company without clearing the current value and selects ANTTEQ directly", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Выбрать контрагента" }));
    expect(screen.getAllByRole("option")).toHaveLength(3);
    await user.click(screen.getByRole("option", { name: "ANTTEQ" }));
    expect(onSelect).toHaveBeenCalledExactlyOnceWith("ANTTEQ");
    expect(screen.getByRole("combobox")).toHaveValue("ANTTEQ");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("filters companies and supports keyboard selection and escape", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect} />);
    const input = screen.getByRole("combobox");
    await user.clear(input);
    await user.type(input, "ant");
    expect(screen.getAllByRole("option")).toHaveLength(1);
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onSelect).toHaveBeenCalledExactlyOnceWith("ANTTEQ");
    await user.click(screen.getByRole("button", { name: "Выбрать контрагента" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("still permits a company outside the suggestions without requesting another profile", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect} />);
    const input = screen.getByRole("combobox");
    await user.clear(input);
    await user.type(input, "Своя организация");
    await user.tab();
    expect(input).toHaveValue("Своя организация");
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
