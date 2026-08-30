/**
 * Créances R. Totalement isolé du capital global et du reste des mois :
 * cette fonction ne prend jamais en paramètre un mois ou un Kharja.
 *
 * solde_R = base + Σ(INCREASE) − Σ(REPAYMENT en valeur NETTE)
 *
 * Remboursement par virement : net = round(brut × 0.92) (−8 %).
 * Remboursement cash : net = brut.
 */
import { assertPositiveCents } from "./money";

export type RDebtType = "INCREASE" | "REPAYMENT";
export type PaymentMethod = "CASH" | "TRANSFER";

/** Montant net réellement déduit de la dette pour un virement (−8 %). */
export function transferNet(grossCents: number): number {
  assertPositiveCents(grossCents, "montant brut virement");
  return Math.round(grossCents * 0.92);
}

/** Net d'un remboursement selon le mode de paiement. */
export function repaymentNet(grossCents: number, method: PaymentMethod): number {
  assertPositiveCents(grossCents, "montant brut remboursement");
  return method === "TRANSFER" ? transferNet(grossCents) : grossCents;
}

export interface RDebtLine {
  type: RDebtType;
  amountNet: number; // centimes déjà nets (= brut si cash, = round(brut×0.92) si virement)
}

export function rDebtBalance(baseAmountCents: number, lines: readonly RDebtLine[]): number {
  let balance = assertPositiveCents(baseAmountCents, "base de dette R");
  for (const line of lines) {
    const net = assertPositiveCents(line.amountNet, "ligne R nette");
    balance += line.type === "INCREASE" ? net : -net;
  }
  return balance;
}
