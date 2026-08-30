/**
 * Socle monétaire. Tous les montants circulent en CENTIMES (entiers).
 * Aucune valeur décimale n'est jamais stockée ni calculée en float :
 * la conversion en euros n'a lieu qu'à l'affichage.
 */

/** Garde-fou : un montant en centimes doit être un entier fini. */
export function assertCents(value: number, label = "montant"): number {
  if (!Number.isInteger(value)) {
    throw new Error(`${label} invalide : ${value} n'est pas un entier de centimes`);
  }
  return value;
}

/** Garde-fou : un montant en centimes positif ou nul. */
export function assertPositiveCents(value: number, label = "montant"): number {
  assertCents(value, label);
  if (value < 0) {
    throw new Error(`${label} invalide : ${value} est négatif`);
  }
  return value;
}

/**
 * Formatage d'affichage uniquement (jamais réinjecté dans un calcul).
 * Ex. 4612785 -> "46 127,85 €"
 */
export function formatEuros(cents: number): string {
  assertCents(cents, "cents");
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const euros = Math.trunc(abs / 100);
  const remainder = String(abs % 100).padStart(2, "0");
  const eurosStr = String(euros).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${sign}${eurosStr},${remainder} €`;
}
