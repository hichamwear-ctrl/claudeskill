import { describe, it, expect } from "vitest";
import { projectPoints } from "@/lib/geo-project";

describe("projectPoints", () => {
  it("returns an empty array for no points", () => {
    expect(projectPoints([], 400, 260)).toEqual([]);
  });

  it("keeps points within the box", () => {
    const pts = projectPoints(
      [
        { lat: 50.84, lng: 4.35 },
        { lat: 50.86, lng: 4.37 },
      ],
      400,
      260,
    );
    for (const p of pts) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(400);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(260);
    }
  });

  it("puts the higher latitude nearer the top (smaller y)", () => {
    const [south, north] = projectPoints(
      [
        { lat: 50.80, lng: 4.35 },
        { lat: 50.90, lng: 4.35 },
      ],
      400,
      260,
    );
    expect(north.y).toBeLessThan(south.y);
  });

  it("handles a single point without dividing by zero", () => {
    const [p] = projectPoints([{ lat: 50.85, lng: 4.35 }], 400, 260);
    expect(Number.isFinite(p.x)).toBe(true);
    expect(Number.isFinite(p.y)).toBe(true);
  });
});
