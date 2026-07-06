import type { ReservationStatus } from "@prisma/client";

export const STATUS_ORDER: ReservationStatus[] = [
  "DEMANDE_ENVOYEE",
  "ACCEPTEE",
  "BARBER_ATTRIBUE",
  "EN_ROUTE",
  "ARRIVE",
  "EN_COURS",
  "TERMINEE",
];

export const STATUS_META: Record<
  ReservationStatus,
  { label: string; description: string; color: string }
> = {
  DEMANDE_ENVOYEE: {
    label: "Demande envoyée",
    description: "Votre demande a bien été reçue.",
    color: "text-sky-400 border-sky-400/30 bg-sky-400/10",
  },
  ACCEPTEE: {
    label: "Acceptée",
    description: "Votre réservation a été acceptée.",
    color: "text-indigo-400 border-indigo-400/30 bg-indigo-400/10",
  },
  BARBER_ATTRIBUE: {
    label: "Barber attribué",
    description: "Un barber vous a été attribué.",
    color: "text-violet-400 border-violet-400/30 bg-violet-400/10",
  },
  EN_ROUTE: {
    label: "En route",
    description: "Votre barber est en route.",
    color: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  },
  ARRIVE: {
    label: "Arrivé",
    description: "Votre barber est arrivé.",
    color: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  },
  EN_COURS: {
    label: "En cours",
    description: "La prestation est en cours.",
    color: "text-gold border-gold/30 bg-gold/10",
  },
  TERMINEE: {
    label: "Terminée",
    description: "La prestation est terminée.",
    color: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  },
  ANNULEE: {
    label: "Annulée",
    description: "La réservation a été annulée.",
    color: "text-rose-400 border-rose-400/30 bg-rose-400/10",
  },
};

/**
 * Statuses a barber can transition to from the current one.
 *
 * Phase 5 workflow: a barber accepts a request (→ ACCEPTEE, provisional
 * assignment) and then waits — only the client can validate that choice
 * (ACCEPTEE → BARBER_ATTRIBUE, handled by the confirm endpoint, not here).
 * "Je suis arrivé" (EN_ROUTE → ARRIVE) ends the visit: GPS, chat and calls
 * all close and the client's rating page appears. The barber can then finalise
 * the accounting (→ TERMINEE).
 */
export const BARBER_NEXT_STATUS: Partial<
  Record<ReservationStatus, ReservationStatus[]>
> = {
  DEMANDE_ENVOYEE: ["ACCEPTEE"],
  ACCEPTEE: ["ANNULEE"],
  BARBER_ATTRIBUE: ["EN_ROUTE", "ANNULEE"],
  EN_ROUTE: ["ARRIVE"],
  ARRIVE: ["EN_COURS", "TERMINEE"],
  EN_COURS: ["TERMINEE"],
};

/** True while a barber has accepted but the client hasn't validated yet. */
export function awaitsClientConfirmation(status: ReservationStatus): boolean {
  return status === "ACCEPTEE";
}

/** True once the client has validated the barber (order definitively booked). */
export function isConfirmed(status: ReservationStatus): boolean {
  return (
    status !== "DEMANDE_ENVOYEE" &&
    status !== "ACCEPTEE" &&
    status !== "ANNULEE"
  );
}

/** GPS sharing runs only while the barber is travelling to the client. */
export function isGpsActive(status: ReservationStatus): boolean {
  return status === "EN_ROUTE";
}

/**
 * The private chat and audio calls are available from the moment the client
 * confirms the barber until the barber arrives (they close at ARRIVE).
 */
export function isConversationActive(status: ReservationStatus): boolean {
  return status === "BARBER_ATTRIBUE" || status === "EN_ROUTE";
}

/** After arrival the client is shown the rating / report page. */
export function isOrderFinished(status: ReservationStatus): boolean {
  return status === "ARRIVE" || status === "EN_COURS" || status === "TERMINEE";
}

export function statusProgress(status: ReservationStatus): number {
  if (status === "ANNULEE") return 0;
  const idx = STATUS_ORDER.indexOf(status);
  return Math.round(((idx + 1) / STATUS_ORDER.length) * 100);
}
