/**
 * Capital restant global.
 *
 * capital_global = Σ(reste_net de chaque mois) + Σ(Kharja : entrées − sorties)
 *
 * Le reste net de chaque mois est fourni PRÉ-CALCULÉ par `monthNetRemainder`
 * (jamais recalculé ici). Cette fonction ne connaît ni le revenu, ni les lignes
 * d'un mois, ni le solde R — séparation stricte des trois totaux.
 */
import { assertCents, assertPositiveCents } from "./money";

export type KharjaType = "IN" | "OUT";

export interface KharjaLine {
  type: KharjaType;
  amount: number; // centimes, positif
}

export function globalCapital(
  monthRemaindersCents: readonly number[],
  kharjaLines: readonly KharjaLine[],
): number {
  let total = 0;
  for (const remainder of monthRemaindersCents) {
    total += assertCents(remainder, "reste de mois");
  }
  for (const line of kharjaLines) {
    const amount = assertPositiveCents(line.amount, "ligne Kharja");
    total += line.type === "IN" ? amount : -amount;
  }
  return total;
}
