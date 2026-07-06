import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { reportSchema } from "@/lib/validations";
import { ok, fail, handleError, rateLimit } from "@/server/api";

/**
 * Client end-of-order feedback that needs human follow-up:
 * "signaler un problème" (PROBLEM) or "besoin d'aide" (HELP). Surfaced to the
 * admin in /admin/reports.
 */
export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { allowed } = rateLimit(`report:${session.user.id}`, {
      limit: 10,
      windowMs: 60_000,
    });
    if (!allowed) return fail("Trop de demandes, patientez.", 429);

    const { reservationId, barberId, type, message } = reportSchema.parse(
      await req.json(),
    );

    // If a reservation is referenced, ensure it belongs to the reporter and
    // derive the barber from it.
    let resolvedBarberId = barberId ?? null;
    if (reservationId) {
      const reservation = await prisma.reservation.findUnique({
        where: { id: reservationId },
        select: { clientId: true, barberId: true },
      });
      if (!reservation || reservation.clientId !== session.user.id)
        return fail("Réservation introuvable", 404);
      resolvedBarberId = reservation.barberId ?? resolvedBarberId;
    }

    const report = await prisma.report.create({
      data: {
        reservationId: reservationId ?? null,
        barberId: resolvedBarberId,
        reporterId: session.user.id,
        type,
        message,
      },
    });
    return ok({ report }, { status: 201 });
  } catch (error) {
    return handleError(error);
  }
}
