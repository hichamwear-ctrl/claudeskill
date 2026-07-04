import type { GeoPoint } from "@/lib/realtime";

export interface XY {
  x: number;
  y: number;
}

/**
 * Projects lat/lng points into a padded [0..width]×[0..height] box for the SVG
 * map. Pure & unit-tested. Equirectangular projection — adequate at city scale.
 */
export function projectPoints(
  points: GeoPoint[],
  width: number,
  height: number,
  padding = 0.15,
): XY[] {
  if (points.length === 0) return [];

  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  let minLat = Math.min(...lats);
  let maxLat = Math.max(...lats);
  let minLng = Math.min(...lngs);
  let maxLng = Math.max(...lngs);

  // Avoid a zero-size span (single point or aligned points).
  if (maxLat - minLat < 1e-4) {
    minLat -= 5e-4;
    maxLat += 5e-4;
  }
  if (maxLng - minLng < 1e-4) {
    minLng -= 5e-4;
    maxLng += 5e-4;
  }

  const padX = width * padding;
  const padY = height * padding;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  return points.map((p) => ({
    x: padX + ((p.lng - minLng) / (maxLng - minLng)) * innerW,
    // invert Y: higher latitude → top of the SVG
    y: padY + (1 - (p.lat - minLat) / (maxLat - minLat)) * innerH,
  }));
}
