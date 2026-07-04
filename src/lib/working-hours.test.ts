import { describe, it, expect } from "vitest";
import {
  isValidRange,
  defaultWeek,
  mergeWeek,
  WEEKDAYS,
} from "@/lib/working-hours";

describe("isValidRange", () => {
  it("accepts a well-ordered range", () => {
    expect(isValidRange("09:00", "18:00")).toBe(true);
  });
  it("rejects start >= end", () => {
    expect(isValidRange("18:00", "09:00")).toBe(false);
    expect(isValidRange("09:00", "09:00")).toBe(false);
  });
  it("rejects malformed times", () => {
    expect(isValidRange("9:00", "18:00")).toBe(false);
    expect(isValidRange("25:00", "26:00")).toBe(false);
  });
});

describe("defaultWeek", () => {
  it("covers 7 days, weekdays enabled and weekend off", () => {
    const w = defaultWeek();
    expect(w).toHaveLength(7);
    expect(w[0].enabled).toBe(false); // Sunday
    expect(w[1].enabled).toBe(true); // Monday
    expect(w[6].enabled).toBe(false); // Saturday
    expect(WEEKDAYS).toHaveLength(7);
  });
});

describe("mergeWeek", () => {
  it("overlays saved rows onto the default week", () => {
    const merged = mergeWeek([
      { weekday: 6, startTime: "10:00", endTime: "14:00", enabled: true },
    ]);
    expect(merged).toHaveLength(7);
    expect(merged[6]).toMatchObject({
      startTime: "10:00",
      endTime: "14:00",
      enabled: true,
    });
    // untouched day keeps defaults
    expect(merged[1].enabled).toBe(true);
  });
});
