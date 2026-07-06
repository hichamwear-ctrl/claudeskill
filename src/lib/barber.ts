import type { BarberLevel } from "@prisma/client";

/** Pure display helpers for barber seniority — shared client & server. */
export const BARBER_LEVELS: Record<BarberLevel, { label: string; short: string }> = {
  JUNIOR: { label: "Junior", short: "Jr" },
  CONFIRME: { label: "Confirmé", short: "Confirmé" },
  EXPERT: { label: "Expert", short: "Expert" },
};

export function barberLevelLabel(level: BarberLevel): string {
  return BARBER_LEVELS[level].label;
}

/** Renders a 0–5 rating as filled/empty stars. */
export function starString(rating: number): string {
  const rounded = Math.round(rating);
  return "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
}
