import { describe, it, expect } from "vitest";
import {
  availableHourStarts,
  hourRangeLabel,
  buildHourSlots,
  type WorkingRange,
} from "@/lib/slots";

describe("hourRangeLabel", () => {
  it("formats an hour as a one-hour range", () => {
    expect(hourRangeLabel(16)).toBe("16 h – 17 h");
  });

  it("wraps around midnight", () => {
    expect(hourRangeLabel(23)).toBe("23 h – 0 h");
  });
});

describe("availableHourStarts", () => {
  it("returns the whole hours covered by a single range", () => {
    const ranges: WorkingRange[] = [{ startTime: "09:00", endTime: "12:00" }];
    expect(availableHourStarts(ranges)).toEqual([9, 10, 11]);
  });

  it("unions overlapping ranges without duplicates", () => {
    const ranges: WorkingRange[] = [
      { startTime: "09:00", endTime: "11:00" },
      { startTime: "10:00", endTime: "13:00" },
    ];
    expect(availableHourStarts(ranges)).toEqual([9, 10, 11, 12]);
  });

  it("omits hours no barber covers (13h gap)", () => {
    const ranges: WorkingRange[] = [
      { startTime: "09:00", endTime: "13:00" },
      { startTime: "14:00", endTime: "16:00" },
    ];
    expect(availableHourStarts(ranges)).not.toContain(13);
    expect(availableHourStarts(ranges)).toEqual([9, 10, 11, 12, 14, 15]);
  });

  it("returns nothing when no barber is available", () => {
    expect(availableHourStarts([])).toEqual([]);
  });
});

describe("buildHourSlots", () => {
  it("labels each hour and enables all slots for a future date", () => {
    const slots = buildHourSlots("2999-01-01", [9, 10]);
    expect(slots).toHaveLength(2);
    expect(slots[0]).toMatchObject({ start: "09:00", label: "9 h – 10 h", disabled: false });
  });

  it("disables past hours on the current day", () => {
    const now = new Date();
    const today = now.toISOString().slice(0, 10);
    const slots = buildHourSlots(today, [0]);
    // 00:00 today is always in the past → disabled.
    expect(slots[0].disabled).toBe(true);
  });
});
