import "server-only";
import { prisma } from "@/server/prisma";

/**
 * Marks a reservation's payment as PAID and issues an invoice (idempotent).
 * Shared by the checkout flow (mock) and the Stripe webhook.
 */
export async function settleReservationPayment(reservationId: string) {
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    include: { payment: true, invoice: true },
  });
  if (!reservation) return;

  if (reservation.payment && reservation.payment.status !== "PAID") {
    await prisma.payment.update({
      where: { reservationId },
      data: { status: "PAID" },
    });
  }

  if (!reservation.invoice) {
    await prisma.invoice.create({
      data: {
        number: `BH-${reservation.reference.slice(0, 8).toUpperCase()}`,
        reservationId,
        userId: reservation.clientId,
        amount: reservation.total,
      },
    });
  }
}
