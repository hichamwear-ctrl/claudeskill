/**
 * High-level realtime publishers (PR #2, Phase 0).
 *
 * Thin, typed wrappers over the transport. These are the ONLY functions the
 * rest of the server will call to emit realtime events. They are defined here
 * but NOT yet wired into the reservation flow — Phase 1 will call
 * `publishReservationStatus` from `notifyStatusChange`, reusing (not
 * duplicating) the existing notification logic.
 */
import "server-only";
import type { ReservationStatus } from "@prisma/client";
import { reservationChannel, type BarberPosition } from "@/lib/realtime";
import { getServerTransport } from "./supabase";

export async function publishReservationStatus(
  reservationId: string,
  status: ReservationStatus,
): Promise<void> {
  await getServerTransport().publish(reservationChannel(reservationId), "status", {
    reservationId,
    status,
    at: Date.now(),
  });
}

export async function publishBarberPosition(
  reservationId: string,
  position: BarberPosition,
): Promise<void> {
  await getServerTransport().publish(reservationChannel(reservationId), "position", {
    reservationId,
    position,
  });
}

export async function publishEta(
  reservationId: string,
  minutes: number,
): Promise<void> {
  await getServerTransport().publish(reservationChannel(reservationId), "eta", {
    reservationId,
    minutes,
    at: Date.now(),
  });
}
