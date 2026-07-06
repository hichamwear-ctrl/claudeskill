/**
 * High-level realtime publishers (Phase 3). The only functions the rest of the
 * server calls to emit realtime events. Fail-soft: realtime errors never break
 * the business action that triggered them.
 */
import "server-only";
import type { ReservationStatus } from "@prisma/client";
import { reservationChannel, type BarberPosition, type GeoPoint } from "@/lib/realtime";
import { getRoutingProvider } from "@/lib/routing";
import { getServerTransport } from "./supabase";

async function safePublish<T>(fn: () => Promise<T>): Promise<void> {
  try {
    await fn();
  } catch (err) {
    console.error("[realtime] publish failed:", err);
  }
}

export async function publishReservationStatus(
  reservationId: string,
  status: ReservationStatus,
): Promise<void> {
  await safePublish(() =>
    getServerTransport().publish(reservationChannel(reservationId), "status", {
      reservationId,
      status,
      at: Date.now(),
    }),
  );
}

export async function publishMessage(
  reservationId: string,
  message: { id: string; senderId: string; body: string },
): Promise<void> {
  await safePublish(() =>
    getServerTransport().publish(reservationChannel(reservationId), "message", {
      reservationId,
      id: message.id,
      senderId: message.senderId,
      body: message.body,
      at: Date.now(),
    }),
  );
}

export async function publishCall(
  reservationId: string,
  call: {
    id: string;
    status: "INITIATED" | "ONGOING" | "ENDED" | "MISSED";
    initiatorId: string;
  },
): Promise<void> {
  await safePublish(() =>
    getServerTransport().publish(reservationChannel(reservationId), "call", {
      reservationId,
      id: call.id,
      status: call.status,
      initiatorId: call.initiatorId,
      at: Date.now(),
    }),
  );
}

export async function publishBarberPosition(
  reservationId: string,
  position: BarberPosition,
  clientPoint?: GeoPoint | null,
): Promise<void> {
  const channel = reservationChannel(reservationId);
  await safePublish(() =>
    getServerTransport().publish(channel, "position", { reservationId, position }),
  );
  if (clientPoint) {
    const eta = await getRoutingProvider().calculateEta(position, clientPoint);
    await safePublish(() =>
      getServerTransport().publish(channel, "eta", {
        reservationId,
        minutes: eta.minutes,
        distanceKm: eta.distanceKm,
        at: Date.now(),
      }),
    );
  }
}
