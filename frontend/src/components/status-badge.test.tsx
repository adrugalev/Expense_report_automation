import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge", () => {
  it.each([
    ["completed", "Готов"],
    ["processing", "Формируется"],
    ["failed", "Ошибка"],
  ] as const)("renders %s status", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
