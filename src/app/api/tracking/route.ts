import { z } from "zod";
import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { publishBarberPosition } from "@/server/realtime/publisher";
import { ok, fail, handleError, rateLimit } from "@/server/api";

const schema = z.object({
  reservationId: z.string(),
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

// Live GPS sharing runs only while the barber is en route; it stops on arrival.
const TRACKABLE = ["EN_ROUTE"];

/**
 * Barber posts a GPS fix for a reservation in progress. Persists a throttled
 * position on the Barber and broadcasts position + ETA to the reservation
 * channel. RBAC: only the assigned barber (or admin) may post.
 */
export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.user) return fail("Non authentifié", 401);
    if (session.user.role === "CLIENT") return fail("Action non autorisée", 403);

    const { reservationId, lat, lng } = schema.parse(await req.json());

    // High-frequency endpoint — bound writes per barber.
    const { allowed } = rateLimit(`tracking:${session.user.id}`, {
      limit: 60,
      windowMs: 60_000,
    });
    if (!allowed) return fail("Trop de mises à jour", 429);

    const reservation = await prisma.reservation.findUnique({
      where: { id: reservationId },
      select: {
        status: true,
        barber: { select: { id: true, userId: true } },
        address: { select: { latitude: true, longitude: true } },
      },
    });
    if (!reservation) return fail("Réservation introuvable", 404);

    const isAssigned = reservation.barber?.userId === session.user.id;
    if (!isAssigned && session.user.role !== "ADMIN")
      return fail("Cette réservation ne vous est pas attribuée", 403);
    if (!TRACKABLE.includes(reservation.status))
      return fail("Le suivi n'est pas actif pour ce statut", 422);

    if (reservation.barber) {
      await prisma.barber.update({
        where: { id: reservation.barber.id },
        data: { currentLat: lat, currentLng: lng },
      });
    }

    const clientPoint =
      reservation.address.latitude != null && reservation.address.longitude != null
        ? { lat: reservation.address.latitude, lng: reservation.address.longitude }
        : null;

    await publishBarberPosition(
      reservationId,
      { lat, lng, at: Date.now() },
      clientPoint,
    );

    return ok({ tracked: true });
  } catch (error) {
    return handleError(error);
  }
}
