import { describe, it, expect } from "vitest";
import {
  isValidUnavailability,
  UNAVAILABILITY_LABELS,
} from "@/lib/unavailability";

describe("isValidUnavailability", () => {
  it("accepts an all-day entry regardless of times", () => {
    expect(isValidUnavailability({ allDay: true })).toBe(true);
  });
  it("requires a well-ordered range when not all-day", () => {
    expect(isValidUnavailability({ allDay: false, startTime: "12:00", endTime: "13:00" })).toBe(true);
    expect(isValidUnavailability({ allDay: false, startTime: "13:00", endTime: "12:00" })).toBe(false);
    expect(isValidUnavailability({ allDay: false, startTime: "12:00", endTime: "12:00" })).toBe(false);
  });
  it("rejects missing or malformed times when not all-day", () => {
    expect(isValidUnavailability({ allDay: false })).toBe(false);
    expect(isValidUnavailability({ allDay: false, startTime: "9:00", endTime: "10:00" })).toBe(false);
  });
  it("exposes labels for every type", () => {
    expect(UNAVAILABILITY_LABELS.BREAK).toBeTruthy();
    expect(UNAVAILABILITY_LABELS.LEAVE).toBeTruthy();
    expect(UNAVAILABILITY_LABELS.OFF).toBeTruthy();
  });
});
