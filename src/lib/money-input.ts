// Conversion saisie utilisateur -> centimes ENTIERS, sans jamais passer par un float
// sur le montant global (on découpe partie entière / décimale à la main).
export function eurosToCents(raw: string): number | null {
  const cleaned = raw.trim().replace(/\s/g, "").replace(",", ".");
  if (cleaned === "") return null;
  if (!/^\d+(\.\d{0,2})?$/.test(cleaned)) return null;
  const [intPart, decPartRaw = ""] = cleaned.split(".");
  const decPart = (decPartRaw + "00").slice(0, 2);
  const cents = Number(intPart) * 100 + Number(decPart);
  return Number.isSafeInteger(cents) ? cents : null;
}
