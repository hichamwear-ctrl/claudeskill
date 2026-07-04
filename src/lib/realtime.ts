/**
 * Realtime contracts — pure & isomorphic (Phase 3).
 * Types + transport interface + channel helpers only. No SDK, no `@/server`.
 */
import type { ReservationStatus } from "@prisma/client";

export interface GeoPoint {
  lat: number;
  lng: number;
}

export interface BarberPosition extends GeoPoint {
  /** epoch ms of the fix */
  at: number;
}

export interface RealtimeEventMap {
  status: { reservationId: string; status: ReservationStatus; at: number };
  position: { reservationId: string; position: BarberPosition };
  eta: { reservationId: string; minutes: number; distanceKm: number; at: number };
}

export type RealtimeEventName = keyof RealtimeEventMap;
export type RealtimeHandler<E extends RealtimeEventName> = (
  payload: RealtimeEventMap[E],
) => void;

export interface RealtimeSubscription {
  unsubscribe(): void;
}

export interface RealtimeTransport {
  publish<E extends RealtimeEventName>(
    channel: string,
    event: E,
    payload: RealtimeEventMap[E],
  ): Promise<void>;
  subscribe<E extends RealtimeEventName>(
    channel: string,
    event: E,
    handler: RealtimeHandler<E>,
  ): RealtimeSubscription;
  unsubscribe(channel: string): void;
}

const RESERVATION_PREFIX = "reservation:";
export function reservationChannel(reservationId: string): string {
  return `${RESERVATION_PREFIX}${reservationId}`;
}
export function parseReservationChannel(channel: string): string | null {
  return channel.startsWith(RESERVATION_PREFIX)
    ? channel.slice(RESERVATION_PREFIX.length) || null
    : null;
}
