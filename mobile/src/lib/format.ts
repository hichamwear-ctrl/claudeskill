/** Utilitaires de formatage purs (localisés FR par défaut). */

/** Montant en euros : `12.5` → « 12,50 € ». `null`/`undefined` → « — ». */
export function formatMoney(amount: number | null | undefined, currency = 'EUR', locale = 'fr-FR'): string {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(amount);
}

/** Date/heure courte localisée. */
export function formatDateTime(iso: string | null | undefined, locale = 'fr-FR'): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

/** Concatène des classes conditionnelles (helper léger). */
export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}
