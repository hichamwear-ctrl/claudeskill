/**
 * ETA / routing abstraction (Phase 3).
 *
 * The default engine reuses the Phase 1 geo helpers (haversine + city-speed
 * estimate). A traffic-aware provider (Google Directions, Mapbox) can be
 * plugged in later by implementing `RoutingProvider` — no component changes.
 */
import { distanceKm, estimateEtaMinutes } from "@/lib/zones";
import type { GeoPoint } from "@/lib/realtime";

export interface EtaResult {
  minutes: number;
  distanceKm: number;
}

export interface RoutingProvider {
  readonly name: string;
  calculateEta(from: GeoPoint, to: GeoPoint): EtaResult | Promise<EtaResult>;
}

/** Straight-line distance + average city speed. Zero dependencies. */
export const haversineRoutingProvider: RoutingProvider = {
  name: "haversine",
  calculateEta(from, to) {
    const d = distanceKm(from, to);
    return { minutes: estimateEtaMinutes(d), distanceKm: Math.round(d * 10) / 10 };
  },
};

let provider: RoutingProvider = haversineRoutingProvider;

/** Swap the active routing engine (e.g. in a bootstrap file). */
export function setRoutingProvider(p: RoutingProvider) {
  provider = p;
}
export function getRoutingProvider(): RoutingProvider {
  return provider;
}
