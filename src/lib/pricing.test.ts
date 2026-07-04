import { describe, it, expect } from "vitest";
import {
  computePrice,
  servicesForType,
  SERVICES,
  TRAVEL_FEE_OUTSIDE_BRUSSELS,
  type BookingPerson,
} from "@/lib/pricing";

const persons: BookingPerson[] = [
  { type: "ADULTE", service: "ADULTE_COUPE" },
  { type: "ADULTE", service: "ADULTE_COUPE_BARBE" },
  { type: "ENFANT", service: "ENFANT_COUPE" },
];

describe("computePrice", () => {
  it("sums subtotal and duration across multiple people", () => {
    const b = computePrice(persons, { insideZone: true });
    expect(b.subtotal).toBe(25 + 35 + 18);
    expect(b.durationMinutes).toBe(30 + 45 + 25);
    expect(b.lines).toHaveLength(3);
  });

  it("applies no travel fee inside Brussels", () => {
    const b = computePrice(persons, { insideZone: true });
    expect(b.travelFee).toBe(0);
    expect(b.total).toBe(b.subtotal);
  });

  it("adds the flat travel fee outside Brussels", () => {
    const b = computePrice(persons, { insideZone: false });
    expect(b.travelFee).toBe(TRAVEL_FEE_OUTSIDE_BRUSSELS);
    expect(b.total).toBe(b.subtotal + TRAVEL_FEE_OUTSIDE_BRUSSELS);
  });

  it("subtracts a discount without going negative", () => {
    const b = computePrice(persons, { insideZone: true, discount: 1000 });
    expect(b.total).toBe(0);
  });

  it("handles an empty selection", () => {
    const b = computePrice([], { insideZone: true });
    expect(b.subtotal).toBe(0);
    expect(b.durationMinutes).toBe(0);
    expect(b.total).toBe(0);
  });
});

describe("servicesForType", () => {
  it("returns only adult services for ADULTE", () => {
    const list = servicesForType("ADULTE");
    expect(list.every((s) => s.type === "ADULTE")).toBe(true);
    expect(list.map((s) => s.key)).toContain("ADULTE_COUPE_BARBE");
  });

  it("returns only child services for ENFANT", () => {
    const list = servicesForType("ENFANT");
    expect(list).toHaveLength(1);
    expect(list[0].key).toBe("ENFANT_COUPE");
  });
});

describe("catalogue integrity", () => {
  it("every service key maps to itself with positive price and duration", () => {
    for (const [key, def] of Object.entries(SERVICES)) {
      expect(def.key).toBe(key);
      expect(def.price).toBeGreaterThan(0);
      expect(def.duration).toBeGreaterThan(0);
    }
  });
});
