/**
 * Map abstraction (Phase 3).
 *
 * The app renders through the declarative `<TrackingMap>` component, whose
 * implementation is selected by `NEXT_PUBLIC_MAPS_PROVIDER`. The imperative
 * `MapProvider` contract below documents the surface a tile provider (Leaflet,
 * Google Maps) must implement to be swapped in without touching call sites.
 */
import type { GeoPoint } from "@/lib/realtime";

export interface MapMarker {
  id: string;
  point: GeoPoint;
  kind: "client" | "barber";
  label?: string;
}

export interface MapProvider {
  createMap(el: HTMLElement, center: GeoPoint, zoom: number): void;
  addMarker(marker: MapMarker): void;
  updateMarker(id: string, point: GeoPoint): void;
  drawRoute(points: GeoPoint[]): void;
  fitBounds(points: GeoPoint[]): void;
}

export interface TrackingMapProps {
  client: GeoPoint | null;
  barber: GeoPoint | null;
  className?: string;
}
