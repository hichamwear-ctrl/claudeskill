/**
 * TVA. Taux fixe 21 % (diviseur 1.21).
 * Formule unique : HTVA = round(total / 1.21) ; TVA = total - HTVA.
 * Résultat toujours entier (centimes).
 */
import { assertPositiveCents } from "./money.js";

const VAT_DIVISOR = 1.21;

/**
 * Brique commune : TVA contenue dans un montant TTC (centimes).
 * Source unique réutilisée par `vat` et `recoveredVat`.
 */
export function vatFromTotal(totalCents: number): number {
  assertPositiveCents(totalCents, "total TVA");
  const htva = Math.round(totalCents / VAT_DIVISOR);
  return totalCents - htva;
}

/**
 * Bouton "TVA" : somme libre d'éléments cochés (revenu et/ou dépenses).
 * Produit le montant d'une ligne NÉGATIVE (catégorie "TVA").
 */
export function vat(selectedCents: readonly number[]): number {
  const total = selectedCents.reduce((sum, c) => sum + assertPositiveCents(c, "élément TVA"), 0);
  return vatFromTotal(total);
}

/**
 * Bouton "Récupérer TVA" : sélection restreinte (Essence / Location Camionnette)
 * garantie par l'appelant. Fonction DISTINCTE de `vat` — aucune déduplication,
 * aucun lien entre les deux calculs. Produit le montant d'une ligne POSITIVE
 * (catégorie "TVA récupérée").
 */
export function recoveredVat(selectedCents: readonly number[]): number {
  const total = selectedCents.reduce((sum, c) => sum + assertPositiveCents(c, "élément TVA récupérée"), 0);
  return vatFromTotal(total);
}
