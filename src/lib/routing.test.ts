import { describe, it, expect } from "vitest";
import { haversineRoutingProvider, getRoutingProvider } from "@/lib/routing";
import { BRUSSELS_CENTER } from "@/lib/zones";

describe("haversineRoutingProvider", () => {
  it("returns zero-ish distance and floored ETA for the same point", async () => {
    const r = await haversineRoutingProvider.calculateEta(BRUSSELS_CENTER, BRUSSELS_CENTER);
    expect(r.distanceKm).toBe(0);
    expect(r.minutes).toBeGreaterThanOrEqual(3);
  });

  it("ETA grows with distance", async () => {
    const near = await haversineRoutingProvider.calculateEta(BRUSSELS_CENTER, {
      lat: 50.85,
      lng: 4.36,
    });
    const far = await haversineRoutingProvider.calculateEta(BRUSSELS_CENTER, {
      lat: 51.05,
      lng: 3.72,
    });
    expect(far.minutes).toBeGreaterThan(near.minutes);
    expect(far.distanceKm).toBeGreaterThan(near.distanceKm);
  });

  it("is the default provider", () => {
    expect(getRoutingProvider().name).toBe("haversine");
  });
});
