/**
 * Brussels service-zone detection.
 *
 * Two strategies, tried in order:
 *  1. Postal code — the 19 Brussels-Capital communes use 1000–1210.
 *  2. Geographic bounding box around Brussels as a coordinate fallback.
 */

const BRUSSELS_POSTAL_MIN = 1000;
const BRUSSELS_POSTAL_MAX = 1210;

// Rough bounding box of the Brussels-Capital Region.
const BRUSSELS_BOUNDS = {
  minLat: 50.76,
  maxLat: 50.92,
  minLng: 4.24,
  maxLng: 4.48,
};

// Approximate geographic centre (Grand-Place) for ETA/distance calculations.
export const BRUSSELS_CENTER = { lat: 50.8467, lng: 4.3499 };

export function isBrusselsPostalCode(postalCode: string): boolean {
  const code = parseInt(postalCode.trim(), 10);
  if (Number.isNaN(code)) return false;
  return code >= BRUSSELS_POSTAL_MIN && code <= BRUSSELS_POSTAL_MAX;
}

export function isInBrusselsBounds(lat: number, lng: number): boolean {
  return (
    lat >= BRUSSELS_BOUNDS.minLat &&
    lat <= BRUSSELS_BOUNDS.maxLat &&
    lng >= BRUSSELS_BOUNDS.minLng &&
    lng <= BRUSSELS_BOUNDS.maxLng
  );
}

export function resolveZone(input: {
  postalCode?: string;
  latitude?: number | null;
  longitude?: number | null;
}): { insideZone: boolean } {
  if (input.postalCode && input.postalCode.trim()) {
    return { insideZone: isBrusselsPostalCode(input.postalCode) };
  }
  if (typeof input.latitude === "number" && typeof input.longitude === "number") {
    return { insideZone: isInBrusselsBounds(input.latitude, input.longitude) };
  }
  // Default to inside zone when we cannot determine — travel fee can be
  // reconciled by the barber on acceptance.
  return { insideZone: true };
}

/** Haversine distance in kilometres — used for ETA estimation. */
export function distanceKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 6371;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** Naive ETA in minutes assuming ~25 km/h average city speed. */
export function estimateEtaMinutes(distance: number): number {
  return Math.max(3, Math.round((distance / 25) * 60));
}

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}
