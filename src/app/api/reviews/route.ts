import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { reviewSchema } from "@/lib/validations";
import { isOrderFinished } from "@/lib/status";
import { notify } from "@/server/notifications";
import { ok, fail, handleError } from "@/server/api";

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { reservationId, rating, comment, photo } = reviewSchema.parse(
      await req.json(),
    );

    const reservation = await prisma.reservation.findUnique({
      where: { id: reservationId },
      include: { review: true, barber: { select: { userId: true } } },
    });
    if (!reservation || reservation.clientId !== session.user.id)
      return fail("Réservation introuvable", 404);
    // The rating page opens as soon as the barber has arrived.
    if (!isOrderFinished(reservation.status))
      return fail("La prestation n'est pas terminée", 422);
    if (!reservation.barberId)
      return fail("Aucun barber à noter", 422);
    if (reservation.review) return fail("Avis déjà enregistré", 409);

    const review = await prisma.review.create({
      data: {
        reservationId,
        authorId: session.user.id,
        barberId: reservation.barberId,
        rating,
        comment,
        photo: photo || null,
      },
    });

    // Recompute the barber's average rating.
    const agg = await prisma.review.aggregate({
      where: { barberId: reservation.barberId },
      _avg: { rating: true },
    });
    await prisma.barber.update({
      where: { id: reservation.barberId },
      data: { rating: agg._avg.rating ?? 5 },
    });

    if (reservation.barber?.userId) {
      await notify(reservation.barber.userId, {
        title: "Nouvel avis",
        body: `Vous avez reçu une note de ${rating}/5.`,
      });
    }

    return ok({ review }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
