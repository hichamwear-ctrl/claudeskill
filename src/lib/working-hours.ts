/** Weekly availability helpers (Phase 3) — pure & unit-tested. */

export const WEEKDAYS = [
  "Dimanche",
  "Lundi",
  "Mardi",
  "Mercredi",
  "Jeudi",
  "Vendredi",
  "Samedi",
] as const;

export interface WorkingHourDraft {
  weekday: number;
  startTime: string; // "HH:MM"
  endTime: string;
  enabled: boolean;
}

/** A valid, enabled range must have start strictly before end (lexicographic on HH:MM works). */
export function isValidRange(startTime: string, endTime: string): boolean {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(startTime) &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(endTime)
    ? startTime < endTime
    : false;
}

/** Monday–Friday 09:00–18:00 enabled, weekend off. */
export function defaultWeek(): WorkingHourDraft[] {
  return WEEKDAYS.map((_, weekday) => ({
    weekday,
    startTime: "09:00",
    endTime: "18:00",
    enabled: weekday >= 1 && weekday <= 5,
  }));
}

/** Merges persisted rows onto the default week so all 7 days are present. */
export function mergeWeek(
  saved: Array<Partial<WorkingHourDraft> & { weekday: number }>,
): WorkingHourDraft[] {
  const base = defaultWeek();
  for (const row of saved) {
    const day = base[row.weekday];
    if (day) Object.assign(day, row);
  }
  return base;
}
