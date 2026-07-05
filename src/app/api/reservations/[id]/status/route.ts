import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { updateStatusSchema } from "@/lib/validations";
import { BARBER_NEXT_STATUS } from "@/lib/status";
import { notifyStatusChange } from "@/server/notifications";
import { awardLoyaltyForReservation } from "@/server/loyalty";
import { ok, fail, handleError } from "@/server/api";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role === "CLIENT")
      return fail("Action non autorisée", 403);

    const { id } = await params;
    const { status } = updateStatusSchema.parse(await req.json());

    const reservation = await prisma.reservation.findUnique({
      where: { id },
      include: { barber: true },
    });
    if (!reservation) return fail("Réservation introuvable", 404);

    // A barber can only manage reservations assigned to them (admins bypass).
    if (session.user.role === "BARBER") {
      const barber = await prisma.barber.findUnique({
        where: { userId: session.user.id },
      });
      const isAssigned = reservation.barberId === barber?.id;
      const isUnassignedRequest =
        reservation.barberId === null && reservation.status === "DEMANDE_ENVOYEE";
      if (!isAssigned && !isUnassignedRequest)
        return fail("Cette réservation ne vous est pas attribuée", 403);

      const allowed = BARBER_NEXT_STATUS[reservation.status] ?? [];
      if (!allowed.includes(status))
        return fail(`Transition ${reservation.status} → ${status} invalide`, 422);

      // Auto-assign the barber when accepting an open request.
      const assignBarber =
        barber && (status === "ACCEPTEE" || status === "BARBER_ATTRIBUE")
          ? { barberId: barber.id }
          : {};

      const updated = await prisma.reservation.update({
        where: { id },
        data: { status, ...assignBarber },
      });
      await notifyStatusChange(
        { id: reservation.id, clientId: reservation.clientId, reference: reservation.reference },
        status,
      );

      if (status === "TERMINEE" && barber) {
        await prisma.barber.update({
          where: { id: barber.id },
          data: { totalJobs: { increment: 1 } },
        });
        await awardLoyaltyForReservation(id);
      }
      return ok({ reservation: updated });
    }

    // Admin: unrestricted transition.
    const updated = await prisma.reservation.update({
      where: { id },
      data: { status },
    });
    await notifyStatusChange(
      { id: reservation.id, clientId: reservation.clientId, reference: reservation.reference },
      status,
    );
    if (status === "TERMINEE") await awardLoyaltyForReservation(id);
    return ok({ reservation: updated });
  } catch (error) {
    return handleError(error);
  }
}
