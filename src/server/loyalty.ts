import "server-only";
import { prisma } from "@/server/prisma";
import { pointsForReservation, pointsForEuro } from "@/lib/loyalty";

const AWARD_REASON = (reservationId: string) => `reservation:${reservationId}`;

/**
 * Awards loyalty points for a completed reservation. Idempotent: a second call
 * for the same reservation is a no-op (guarded by a unique reason marker).
 */
export async function awardLoyaltyForReservation(reservationId: string) {
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    select: { clientId: true, total: true },
  });
  if (!reservation) return;

  const already = await prisma.loyaltyTransaction.findFirst({
    where: { userId: reservation.clientId, reason: AWARD_REASON(reservationId) },
  });
  if (already) return;

  const points = pointsForReservation(reservation.total);
  if (points <= 0) return;

  await prisma.$transaction([
    prisma.loyaltyTransaction.create({
      data: {
        userId: reservation.clientId,
        points,
        reason: AWARD_REASON(reservationId),
      },
    }),
    prisma.user.update({
      where: { id: reservation.clientId },
      data: { loyaltyPoints: { increment: points } },
    }),
  ]);
}

/** Redeems points into a single-use promo code. Returns the generated code. */
export async function redeemLoyalty(userId: string, euro: number): Promise<string> {
  const cost = pointsForEuro(euro);
  if (cost === null) throw new Error("Montant de bon invalide");

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { loyaltyPoints: true },
  });
  if (!user || user.loyaltyPoints < cost) throw new Error("Points insuffisants");

  const code = `FID-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;

  await prisma.$transaction([
    prisma.promoCode.create({
      data: {
        code,
        description: `Bon fidélité ${euro} €`,
        amountOff: euro,
        maxUses: 1,
        active: true,
      },
    }),
    prisma.loyaltyTransaction.create({
      data: { userId, points: -cost, reason: `redeem:${euro}eur` },
    }),
    prisma.user.update({
      where: { id: userId },
      data: { loyaltyPoints: { decrement: cost } },
    }),
  ]);

  return code;
}
