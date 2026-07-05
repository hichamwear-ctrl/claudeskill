import "server-only";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { prisma } from "@/server/prisma";
import { settleReservationPayment } from "@/server/invoices";
import { SERVICES } from "@/lib/pricing";

const GOLD = rgb(0.72, 0.58, 0.16);
const DARK = rgb(0.1, 0.1, 0.1);
const GREY = rgb(0.45, 0.45, 0.45);

// Plain-ASCII money to stay within the PDF font's WinAnsi encoding.
const money = (n: number) => `${n.toFixed(2)} EUR`;

/**
 * Generates a real PDF invoice for a reservation. Ensures an Invoice row
 * exists (idempotent) so the numbering + history stay consistent.
 */
export async function generateInvoicePdf(reservationId: string): Promise<Uint8Array | null> {
  const reservation = await prisma.reservation.findUnique({
    where: { id: reservationId },
    include: { persons: true, address: true, client: true, invoice: true },
  });
  if (!reservation) return null;

  // Make sure a persisted invoice/number exists for paid or completed jobs.
  if (!reservation.invoice) {
    await settleReservationPayment(reservationId).catch(() => null);
  }
  const number = `BH-${reservation.reference.slice(0, 8).toUpperCase()}`;

  const pdf = await PDFDocument.create();
  const page = pdf.addPage([595.28, 841.89]); // A4
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const { width } = page.getSize();
  let y = 790;

  const text = (
    s: string,
    x: number,
    yy: number,
    size = 10,
    f = font,
    color = DARK,
  ) => page.drawText(s, { x, y: yy, size, font: f, color });

  // Header
  text("Barber", 50, y, 22, bold, DARK);
  text("Home", 122, y, 22, bold, GOLD);
  text("Facture", width - 160, y, 16, bold, DARK);
  y -= 18;
  text("Le barber premium a domicile - Bruxelles", 50, y, 9, font, GREY);
  text(number, width - 160, y, 10, font, GREY);
  y -= 6;
  page.drawLine({
    start: { x: 50, y },
    end: { x: width - 50, y },
    thickness: 2,
    color: GOLD,
  });
  y -= 30;

  // Client
  text("Facture a :", 50, y, 10, bold);
  y -= 15;
  text(`${reservation.client.firstName} ${reservation.client.lastName}`, 50, y);
  y -= 14;
  text(
    `${reservation.address.street} ${reservation.address.number ?? ""}`.trim(),
    50,
    y,
    9,
    font,
    GREY,
  );
  y -= 12;
  text(
    `${reservation.address.postalCode} ${reservation.address.city}`,
    50,
    y,
    9,
    font,
    GREY,
  );
  y -= 12;
  text(`Date : ${reservation.createdAt.toLocaleDateString("fr-BE")}`, 50, y, 9, font, GREY);
  y -= 30;

  // Table header
  text("Prestation", 50, y, 10, bold);
  text("Duree", 340, y, 10, bold);
  text("Prix", width - 110, y, 10, bold);
  y -= 8;
  page.drawLine({ start: { x: 50, y }, end: { x: width - 50, y }, thickness: 1, color: GREY });
  y -= 18;

  for (const p of reservation.persons) {
    const def = SERVICES[p.service];
    text(def.name, 50, y);
    text(`${p.duration} min`, 340, y, 10, font, GREY);
    text(money(p.price), width - 110, y);
    y -= 18;
  }

  y -= 6;
  page.drawLine({ start: { x: 320, y }, end: { x: width - 50, y }, thickness: 1, color: GREY });
  y -= 20;

  const totalsRow = (label: string, value: string, strong = false) => {
    text(label, 340, y, 10, strong ? bold : font, strong ? DARK : GREY);
    text(value, width - 110, y, strong ? 12 : 10, strong ? bold : font, strong ? DARK : DARK);
    y -= 18;
  };
  totalsRow("Sous-total", money(reservation.subtotal));
  totalsRow("Deplacement", money(reservation.travelFee));
  totalsRow("Remise", `-${money(reservation.discount)}`);
  y -= 4;
  totalsRow("Total", money(reservation.total), true);

  y -= 40;
  text("Merci de votre confiance. Barber Home - TVA BE0000.000.000", 50, y, 9, font, GREY);

  return pdf.save();
}
