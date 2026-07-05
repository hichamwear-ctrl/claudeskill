import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { getPaymentProvider } from "@/server/payments";
import { settleReservationPayment } from "@/server/invoices";
import { ok, fail, handleError, rateLimit } from "@/server/api";

const schema = z.object({ reservationId: z.string() });

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { allowed } = rateLimit(`checkout:${session.user.id}`, { limit: 15 });
    if (!allowed) return fail("Trop de requêtes", 429);

    const { reservationId } = schema.parse(await req.json());
    const reservation = await prisma.reservation.findUnique({
      where: { id: reservationId },
      include: { payment: true },
    });
    if (!reservation || reservation.clientId !== session.user.id)
      return fail("Réservation introuvable", 404);
    if (!reservation.payment) return fail("Aucun paiement associé", 422);
    if (reservation.payment.status === "PAID")
      return fail("Déjà payé", 409);

    const base = process.env.AUTH_URL ?? "http://localhost:3000";
    const result = await getPaymentProvider().createCheckout({
      reservationId,
      amount: reservation.total,
      currency: "EUR",
      description: `Barber Home — réservation ${reservation.reference.slice(0, 6).toUpperCase()}`,
      successUrl: `${base}/client/payments?status=success`,
      cancelUrl: `${base}/client/payments?status=cancel`,
    });

    // Inline settlement (mock provider) — no redirect needed.
    if (result.status === "paid") {
      await settleReservationPayment(reservationId);
      return ok({ paid: true });
    }
    return ok({ url: result.url });
  } catch (error) {
    return handleError(error);
  }
}
