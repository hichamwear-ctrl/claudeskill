/**
 * Realtime contracts — pure & isomorphic (PR #2, Phase 0).
 *
 * This module contains ONLY types, the transport interface and channel-name
 * helpers. No SDK, no `@/server/*`, no side effects — so it can be imported
 * safely from both client components and server code without breaking the
 * server/client boundary established in PR #1.
 *
 * The canonical `RealtimeTransport` interface lives here (client-safe) and is
 * re-exported from `src/server/realtime/transport.ts` for server ergonomics.
 */
import type { ReservationStatus } from "@prisma/client";

export interface BarberPosition {
  lat: number;
  lng: number;
  /** epoch ms when the fix was taken */
  at: number;
}

/** Strongly-typed event payloads carried over a reservation channel. */
export interface RealtimeEventMap {
  status: { reservationId: string; status: ReservationStatus; at: number };
  position: { reservationId: string; position: BarberPosition };
  eta: { reservationId: string; minutes: number; at: number };
}

export type RealtimeEventName = keyof RealtimeEventMap;

export type RealtimeHandler<E extends RealtimeEventName> = (
  payload: RealtimeEventMap[E],
) => void;

export interface RealtimeSubscription {
  unsubscribe(): void;
}

/**
 * Transport abstraction. Every realtime interaction goes through this
 * interface — no React component or server module ever touches the Supabase
 * SDK directly, so the provider can be swapped (Socket.io, …) without changes
 * elsewhere.
 */
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

// --- Channel naming (single source of truth) ---------------------------------

const RESERVATION_PREFIX = "reservation:";

export function reservationChannel(reservationId: string): string {
  return `${RESERVATION_PREFIX}${reservationId}`;
}

/** Extracts the reservationId from a channel name, or null if it doesn't match. */
export function parseReservationChannel(channel: string): string | null {
  return channel.startsWith(RESERVATION_PREFIX)
    ? channel.slice(RESERVATION_PREFIX.length) || null
    : null;
}
