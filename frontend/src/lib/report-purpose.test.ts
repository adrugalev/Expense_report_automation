import { describe, expect, it } from "vitest";
import { switchReportPurpose } from "@/lib/report-purpose";

describe("switchReportPurpose", () => {
  it("does not transfer the gift purpose to a business trip", () => {
    const gifts = switchReportPurpose("business_trip", "gifts", "", { business_trip: "", gifts: "" }, "Цель подарков");
    const trip = switchReportPurpose("gifts", "business_trip", gifts.purpose, gifts.savedPurposes, "Цель подарков");

    expect(gifts.purpose).toBe("Цель подарков");
    expect(trip.purpose).toBe("");
  });

  it("restores a purpose only for its own report type", () => {
    const gifts = switchReportPurpose("business_trip", "gifts", "Монтаж лифтов", { business_trip: "", gifts: "" }, "Цель подарков");
    const trip = switchReportPurpose("gifts", "business_trip", gifts.purpose, gifts.savedPurposes, "Цель подарков");

    expect(trip.purpose).toBe("Монтаж лифтов");
  });
});
