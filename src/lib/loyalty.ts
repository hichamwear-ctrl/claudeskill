/** Loyalty program rules (Phase 3) — pure & unit-tested. */

/** Points earned per euro spent on a completed reservation. */
export const POINTS_PER_EURO = 1;

/** 100 points → 5 € voucher. */
export const REDEEM_STEP_POINTS = 100;
export const REDEEM_STEP_EURO = 5;

export interface Tier {
  name: string;
  min: number;
  perk: string;
}

export const TIERS: Tier[] = [
  { name: "Bronze", min: 0, perk: "Bienvenue chez Barber Home" },
  { name: "Argent", min: 200, perk: "Créneaux prioritaires" },
  { name: "Or", min: 500, perk: "-5% permanents" },
  { name: "Platine", min: 1000, perk: "Barber attitré & avantages VIP" },
];

export function pointsForReservation(total: number): number {
  return Math.max(0, Math.round(total * POINTS_PER_EURO));
}

export function tierFor(points: number): { current: Tier; next: Tier | null; toNext: number } {
  let current = TIERS[0];
  for (const t of TIERS) if (points >= t.min) current = t;
  const next = TIERS.find((t) => t.min > points) ?? null;
  return { current, next, toNext: next ? next.min - points : 0 };
}

/** Largest euro voucher redeemable from a points balance (multiples of the step). */
export function maxRedeemableEuro(points: number): number {
  return Math.floor(points / REDEEM_STEP_POINTS) * REDEEM_STEP_EURO;
}

/** Points cost for a requested euro voucher (must be a multiple of the step). */
export function pointsForEuro(euro: number): number | null {
  if (euro <= 0 || euro % REDEEM_STEP_EURO !== 0) return null;
  return (euro / REDEEM_STEP_EURO) * REDEEM_STEP_POINTS;
}
