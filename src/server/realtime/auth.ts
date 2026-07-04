/**
 * Channel authorization & HMAC-signed tokens (Phase 3).
 * A user may join `reservation:{id}` only as its client, its assigned barber,
 * or an ADMIN. Pure predicate is unit-tested; DB lookup uses a lazy import.
 */
import { createHmac, timingSafeEqual } from "node:crypto";
import type { Role } from "@prisma/client";

export interface ChannelPrincipal {
  userId: string;
  role: Role;
}
export interface ReservationParticipants {
  clientId: string;
  barberUserId: string | null;
}

export function canJoinReservationChannel(
  principal: ChannelPrincipal,
  r: ReservationParticipants,
): boolean {
  if (principal.role === "ADMIN") return true;
  if (r.clientId === principal.userId) return true;
  return !!r.barberUserId && r.barberUserId === principal.userId;
}

function secret(): string {
  const s = process.env.REALTIME_CHANNEL_SECRET ?? process.env.AUTH_SECRET;
  if (!s) throw new Error("REALTIME_CHANNEL_SECRET (or AUTH_SECRET) required");
  return s;
}
function sign(body: string): string {
  return createHmac("sha256", secret()).update(body).digest("base64url");
}

export interface ChannelTokenPayload {
  channel: string;
  userId: string;
  exp: number;
}

export function signChannelToken(
  payload: Omit<ChannelTokenPayload, "exp">,
  ttlSeconds = 3600,
): string {
  const full = { ...payload, exp: Math.floor(Date.now() / 1000) + ttlSeconds };
  const body = Buffer.from(JSON.stringify(full)).toString("base64url");
  return `${body}.${sign(body)}`;
}

export function verifyChannelToken(
  token: string,
  expected: { channel: string; userId: string },
): boolean {
  const [body, sig] = token.split(".");
  if (!body || !sig) return false;
  const a = Buffer.from(sig);
  const b = Buffer.from(sign(body));
  if (a.length !== b.length || !timingSafeEqual(a, b)) return false;
  let p: ChannelTokenPayload;
  try {
    p = JSON.parse(Buffer.from(body, "base64url").toString());
  } catch {
    return false;
  }
  if (p.exp < Math.floor(Date.now() / 1000)) return false;
  return p.channel === expected.channel && p.userId === expected.userId;
}

export async function authorizeReservationChannel(
  principal: ChannelPrincipal,
  reservationId: string,
): Promise<boolean> {
  const { prisma } = await import("@/server/prisma");
  const r = await prisma.reservation.findUnique({
    where: { id: reservationId },
    select: { clientId: true, barber: { select: { userId: true } } },
  });
  if (!r) return false;
  return canJoinReservationChannel(principal, {
    clientId: r.clientId,
    barberUserId: r.barber?.userId ?? null,
  });
}
