import { describe, expect, it } from "vitest";
import { cn, formatBytes } from "@/lib/utils";

describe("formatBytes", () => {
  it("formats byte, kilobyte and megabyte values", () => {
    expect(formatBytes(512)).toBe("512 Б");
    expect(formatBytes(2048)).toBe("2.0 КБ");
    expect(formatBytes(2 * 1024 * 1024)).toBe("2.0 МБ");
  });
});

describe("cn", () => {
  it("merges conflicting Tailwind classes", () => {
    expect(cn("px-2", false && "hidden", "px-4")).toBe("px-4");
  });
});
