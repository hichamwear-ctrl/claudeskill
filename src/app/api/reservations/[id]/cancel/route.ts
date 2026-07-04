import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { notifyStatusChange } from "@/lib/notifications";
import { ok, fail, handleError } from "@/lib/api";

const CANCELLABLE = ["DEMANDE_ENVOYEE", "ACCEPTEE", "BARBER_ATTRIBUE"];

export async function PATCH(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);

    const { id } = await params;
    const reservation = await prisma.reservation.findUnique({ where: { id } });
    if (!reservation || reservation.clientId !== session.user.id)
      return fail("Réservation introuvable", 404);

    if (!CANCELLABLE.includes(reservation.status))
      return fail("Cette réservation ne peut plus être annulée", 422);

    const updated = await prisma.reservation.update({
      where: { id },
      data: { status: "ANNULEE" },
    });
    await notifyStatusChange(reservation.clientId, reservation.reference, "ANNULEE");
    return ok({ reservation: updated });
  } catch (error) {
    return handleError(error);
  }
}
