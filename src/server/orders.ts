import "server-only";
import { prisma } from "./prisma";
import { notify } from "./notifications";
import { publishReservationStatus } from "./realtime/publisher";

/**
 * Phase 5 acceptance workflow.
 *
 *   client demande ─► barber accepte (ACCEPTEE, provisoire)
 *                       └─► client confirme (BARBER_ATTRIBUE) ─► chat + appels
 *                       └─► client refuse   (retour DEMANDE_ENVOYEE)
 *
 * All the DB mutations for that handshake live here so the API routes stay thin
 * and the rules are testable in one place.
 */

const fullName = (u: { firstName: string; lastName: string }) =>
  `${u.firstName} ${u.lastName}`;

/** A barber accepts an open request (provisional assignment, awaits client). */
export async function acceptRequest(reservationId: string, barberUserId: string) {
  const barber = await prisma.barber.findUnique({
    where: { userId: barberUserId },
    include: { user: true },
  });
  if (!barber) throw new OrderError("Profil barber introuvable", 403);

  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
  });
  if (!reservation) throw new OrderError("Réservation introuvable", 404);
  if (reservation.status !== "DEMANDE_ENVOYEE" || reservation.barberId)
    throw new OrderError("Cette demande n'est plus disponible", 409);
  if (reservation.declinedBarberIds.includes(barber.id))
    throw new OrderError("Vous avez déjà refusé cette demande", 409);

  const updated = await prisma.reservation.update({
    where: { id: reservationId },
    data: { status: "ACCEPTEE", barberId: barber.id },
  });

  await notify(reservation.clientId, {
    title: "Demande acceptée",
    body: `${fullName(barber.user)} a accepté votre demande. Consultez son profil pour confirmer.`,
  });
  await publishReservationStatus(reservationId, "ACCEPTEE").catch(() => {});
  return updated;
}

/** A barber declines an open request; they won't be offered it again. */
export async function declineRequest(reservationId: string, barberUserId: string) {
  const barber = await prisma.barber.findUnique({ where: { userId: barberUserId } });
  if (!barber) throw new OrderError("Profil barber introuvable", 403);

  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
  });
  if (!reservation) throw new OrderError("Réservation introuvable", 404);
  if (reservation.status !== "DEMANDE_ENVOYEE")
    throw new OrderError("Cette demande n'est plus disponible", 409);

  return prisma.reservation.update({
    where: { id: reservationId },
    data: { declinedBarberIds: { push: barber.id } },
  });
}

/** The client validates or rejects the barber who accepted. */
export async function decideBarber(
  reservationId: string,
  clientId: string,
  decision: "CONFIRM" | "REFUSE",
) {
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    include: { barber: { include: { user: true } } },
  });
  if (!reservation) throw new OrderError("Réservation introuvable", 404);
  if (reservation.clientId !== clientId)
    throw new OrderError("Cette réservation ne vous appartient pas", 403);
  if (reservation.status !== "ACCEPTEE" || !reservation.barber)
    throw new OrderError("Aucun barber à confirmer", 409);

  if (decision === "CONFIRM") {
    const updated = await prisma.reservation.update({
      where: { id: reservationId },
      data: { status: "BARBER_ATTRIBUE" },
    });
    await notify(reservation.barber.userId, {
      title: "Barber confirmé",
      body: `Votre client a confirmé la réservation ${reservation.reference}. Le chat est ouvert.`,
    });
    await publishReservationStatus(reservationId, "BARBER_ATTRIBUE").catch(() => {});
    return updated;
  }

  // REFUSE — release the barber, exclude them, re-open to the pool.
  const refusedBarberId = reservation.barberId!;
  const updated = await prisma.reservation.update({
    where: { id: reservationId },
    data: {
      status: "DEMANDE_ENVOYEE",
      barberId: null,
      declinedBarberIds: { push: refusedBarberId },
    },
  });
  await notify(reservation.barber.userId, {
    title: "Réservation non retenue",
    body: `Le client n'a pas retenu votre proposition pour ${reservation.reference}.`,
  });
  await publishReservationStatus(reservationId, "DEMANDE_ENVOYEE").catch(() => {});
  return updated;
}

export interface OrderParticipant {
  reservationId: string;
  status: import("@prisma/client").ReservationStatus;
  /** The signed-in user's role in this order. */
  role: "client" | "barber";
  clientId: string;
  barberUserId: string | null;
  /** The other party (message/call recipient). */
  otherUserId: string | null;
}

/**
 * Resolves the current user's participation in an order and rejects anyone who
 * is neither the client nor the assigned barber (admins are allowed as barber).
 */
export async function getOrderParticipant(
  reservationId: string,
  userId: string,
  isAdmin = false,
): Promise<OrderParticipant> {
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    select: {
      id: true,
      status: true,
      clientId: true,
      barber: { select: { userId: true } },
    },
  });
  if (!reservation) throw new OrderError("Réservation introuvable", 404);

  const barberUserId = reservation.barber?.userId ?? null;
  const isClient = reservation.clientId === userId;
  const isBarber = barberUserId === userId || isAdmin;
  if (!isClient && !isBarber)
    throw new OrderError("Accès refusé à cette réservation", 403);

  return {
    reservationId: reservation.id,
    status: reservation.status,
    role: isClient ? "client" : "barber",
    clientId: reservation.clientId,
    barberUserId,
    otherUserId: isClient ? barberUserId : reservation.clientId,
  };
}

/** Small typed error so routes can map to the right HTTP status. */
export class OrderError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.status = status;
  }
}
