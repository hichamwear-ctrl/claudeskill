/**
 * Reste net d'un mois. NE dépend JAMAIS du Kharja (rattachement purement visuel).
 *
 * reste = revenu + Σ(lignes ADDITION) − Σ(lignes SUBTRACTION)
 *
 * Les lignes "TVA" (négative) et "TVA récupérée" (positive) sont de simples
 * lignes signées : elles entrent ici via leur type de catégorie, sans traitement
 * spécial. Plusieurs lignes TVA / TVA récupérée peuvent coexister dans un mois.
 */
import { assertCents, assertPositiveCents } from "./money.js";

export type CategoryType = "ADDITION" | "SUBTRACTION";

export interface MonthLine {
  amount: number; // centimes, toujours positif ; le signe vient du type
  type: CategoryType;
}

export function monthNetRemainder(clientPaymentCents: number, lines: readonly MonthLine[]): number {
  let remainder = assertCents(clientPaymentCents, "revenu du mois");
  for (const line of lines) {
    const amount = assertPositiveCents(line.amount, "ligne du mois");
    remainder += line.type === "ADDITION" ? amount : -amount;
  }
  return remainder;
}
