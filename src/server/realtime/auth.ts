/**
 * Channel authorization & signed tokens (PR #2, Phase 0).
 *
 * A user may only join `reservation:{id}` if they are:
 *   - the client who owns the reservation, or
 *   - the barber assigned to it, or
 *   - an ADMIN.
 *
 * The pure predicate `canJoinReservationChannel` is unit-tested. `authorize*`
 * fetches the reservation (Prisma imported lazily so the pure helpers stay
 * dependency-free and testable without a DB). Tokens are HMAC-signed so the
 * client cannot forge channel membership.
 */
import { createHmac, timingSafeEqual } from "node:crypto";
import type { Role } from "@prisma/client";

export interface ChannelPrincipal {
  userId: string;
  role: Role;
}

export interface ReservationParticipants {
  clientId: string;
  /** User id of the assigned barber (Barber.userId), or null if unassigned. */
  barberUserId: string | null;
}

/** Pure RBAC predicate — no side effects, fully unit-testable. */
export function canJoinReservationChannel(
  principal: ChannelPrincipal,
  reservation: ReservationParticipants,
): boolean {
  if (principal.role === "ADMIN") return true;
  if (reservation.clientId === principal.userId) return true;
  if (reservation.barberUserId && reservation.barberUserId === principal.userId) {
    return true;
  }
  return false;
}

// --- Signed channel tokens ---------------------------------------------------

export interface ChannelTokenPayload {
  channel: string;
  userId: string;
  /** expiry, epoch seconds */
  exp: number;
}

function secret(): string {
  const s = process.env.REALTIME_CHANNEL_SECRET ?? process.env.AUTH_SECRET;
  if (!s) throw new Error("REALTIME_CHANNEL_SECRET (or AUTH_SECRET) is required");
  return s;
}

function b64url(input: string): string {
  return Buffer.from(input).toString("base64url");
}

function sign(body: string): string {
  return createHmac("sha256", secret()).update(body).digest("base64url");
}

export function signChannelToken(
  payload: Omit<ChannelTokenPayload, "exp">,
  ttlSeconds = 60 * 60,
): string {
  const full: ChannelTokenPayload = {
    ...payload,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
  };
  const body = b64url(JSON.stringify(full));
  return `${body}.${sign(body)}`;
}

export function verifyChannelToken(
  token: string,
  expected: { channel: string; userId: string },
): boolean {
  const [body, sig] = token.split(".");
  if (!body || !sig) return false;

  const expectedSig = sign(body);
  const a = Buffer.from(sig);
  const b = Buffer.from(expectedSig);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return false;

  let payload: ChannelTokenPayload;
  try {
    payload = JSON.parse(Buffer.from(body, "base64url").toString());
  } catch {
    return false;
  }

  if (payload.exp < Math.floor(Date.now() / 1000)) return false;
  return payload.channel === expected.channel && payload.userId === expected.userId;
}

// --- DB-backed authorization -------------------------------------------------

/** Resolves reservation participants and applies the pure predicate. */
export async function authorizeReservationChannel(
  principal: ChannelPrincipal,
  reservationId: string,
): Promise<boolean> {
  const { prisma } = await import("@/server/prisma");
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    select: { clientId: true, barber: { select: { userId: true } } },
  });
  if (!reservation) return false;

  return canJoinReservationChannel(principal, {
    clientId: reservation.clientId,
    barberUserId: reservation.barber?.userId ?? null,
  });
}
