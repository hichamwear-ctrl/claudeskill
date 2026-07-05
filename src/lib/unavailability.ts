/** Barber date-specific unavailability helpers (Phase 3) — pure & unit-tested. */

export type UnavailabilityType = "BREAK" | "LEAVE" | "OFF";

export const UNAVAILABILITY_LABELS: Record<UnavailabilityType, string> = {
  BREAK: "Pause",
  LEAVE: "Congé",
  OFF: "Indisponible",
};

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

export function isValidUnavailability(input: {
  allDay: boolean;
  startTime?: string | null;
  endTime?: string | null;
}): boolean {
  if (input.allDay) return true;
  if (!input.startTime || !input.endTime) return false;
  if (!TIME_RE.test(input.startTime) || !TIME_RE.test(input.endTime)) return false;
  return input.startTime < input.endTime;
}
