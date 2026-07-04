import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { fail } from "@/server/api";
import { SERVICES } from "@/lib/pricing";
import { formatCurrency, formatDateTime } from "@/lib/utils";

/**
 * Renders a printable invoice (Ctrl/Cmd+P → Save as PDF).
 * Replace with a server-side PDF generator (e.g. @react-pdf/renderer) later.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);

  const { id } = await params;
  const reservation = await prisma.reservation.findUnique({
    where: { id },
    include: { persons: true, address: true, client: true },
  });

  if (!reservation) return fail("Introuvable", 404);
  if (
    reservation.clientId !== session.user.id &&
    session.user.role !== "ADMIN"
  )
    return fail("Accès refusé", 403);

  const number = `BH-${reservation.reference.slice(0, 8).toUpperCase()}`;
  const rows = reservation.persons
    .map(
      (p) =>
        `<tr><td>${SERVICES[p.service].name}</td><td>${p.duration} min</td><td style="text-align:right">${formatCurrency(p.price)}</td></tr>`,
    )
    .join("");

  const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Facture ${number}</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 24px;color:#111}
  .head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #D4AF37;padding-bottom:16px}
  h1{font-size:22px;margin:0}.gold{color:#B8942A}
  table{width:100%;border-collapse:collapse;margin-top:24px}
  td,th{padding:10px 8px;border-bottom:1px solid #eee;font-size:14px}
  th{text-align:left;color:#888;font-weight:600}
  .totals{margin-top:16px;margin-left:auto;width:260px;font-size:14px}
  .totals div{display:flex;justify-content:space-between;padding:4px 0}
  .grand{font-weight:700;font-size:18px;border-top:2px solid #111;margin-top:8px;padding-top:8px}
  .muted{color:#888;font-size:13px}
</style></head><body>
  <div class="head">
    <div><h1>Barber<span class="gold">Home</span></h1><p class="muted">Le barber premium à domicile · Bruxelles</p></div>
    <div style="text-align:right"><strong>Facture ${number}</strong><br><span class="muted">${formatDateTime(reservation.createdAt)}</span></div>
  </div>
  <p><strong>Client :</strong> ${reservation.client.firstName} ${reservation.client.lastName}<br>
  <span class="muted">${reservation.address.street} ${reservation.address.number ?? ""}, ${reservation.address.postalCode} ${reservation.address.city}</span></p>
  <table><thead><tr><th>Prestation</th><th>Durée</th><th style="text-align:right">Prix</th></tr></thead><tbody>${rows}</tbody></table>
  <div class="totals">
    <div><span>Sous-total</span><span>${formatCurrency(reservation.subtotal)}</span></div>
    <div><span>Déplacement</span><span>${formatCurrency(reservation.travelFee)}</span></div>
    <div><span>Remise</span><span>-${formatCurrency(reservation.discount)}</span></div>
    <div class="grand"><span>Total</span><span>${formatCurrency(reservation.total)}</span></div>
  </div>
  <p class="muted" style="margin-top:40px">Merci de votre confiance. Barber Home — TVA BE0000.000.000</p>
</body></html>`;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
