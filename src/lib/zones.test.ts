import { describe, it, expect } from "vitest";
import {
  isBrusselsPostalCode,
  isInBrusselsBounds,
  resolveZone,
  distanceKm,
  estimateEtaMinutes,
  BRUSSELS_CENTER,
} from "@/lib/zones";

describe("isBrusselsPostalCode", () => {
  it("accepts the 1000–1210 range", () => {
    expect(isBrusselsPostalCode("1000")).toBe(true);
    expect(isBrusselsPostalCode("1050")).toBe(true);
    expect(isBrusselsPostalCode("1210")).toBe(true);
  });
  it("rejects codes outside the range or invalid", () => {
    expect(isBrusselsPostalCode("1300")).toBe(false);
    expect(isBrusselsPostalCode("9000")).toBe(false);
    expect(isBrusselsPostalCode("abc")).toBe(false);
  });
});

describe("resolveZone", () => {
  it("uses the postal code first", () => {
    expect(resolveZone({ postalCode: "1050" }).insideZone).toBe(true);
    expect(resolveZone({ postalCode: "4000" }).insideZone).toBe(false);
  });
  it("falls back to coordinates when no postal code", () => {
    expect(
      resolveZone({ latitude: BRUSSELS_CENTER.lat, longitude: BRUSSELS_CENTER.lng })
        .insideZone,
    ).toBe(true);
    expect(resolveZone({ latitude: 51.2, longitude: 4.4 }).insideZone).toBe(false);
  });
  it("defaults to inside zone when nothing is provided", () => {
    expect(resolveZone({}).insideZone).toBe(true);
  });
});

describe("geo helpers", () => {
  it("bounds contain the centre", () => {
    expect(isInBrusselsBounds(BRUSSELS_CENTER.lat, BRUSSELS_CENTER.lng)).toBe(true);
  });
  it("distance is zero for the same point and positive otherwise", () => {
    expect(distanceKm(BRUSSELS_CENTER, BRUSSELS_CENTER)).toBeCloseTo(0, 5);
    expect(distanceKm(BRUSSELS_CENTER, { lat: 51.05, lng: 3.72 })).toBeGreaterThan(40);
  });
  it("ETA is at least the floor and grows with distance", () => {
    expect(estimateEtaMinutes(0)).toBeGreaterThanOrEqual(3);
    expect(estimateEtaMinutes(25)).toBeGreaterThan(estimateEtaMinutes(5));
  });
});
