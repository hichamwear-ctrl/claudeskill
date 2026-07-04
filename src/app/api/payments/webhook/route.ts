import { getPaymentProvider } from "@/server/payments";
import { settleReservationPayment } from "@/server/invoices";

/**
 * Payment provider webhook (Stripe). Reads the raw body, verifies the
 * signature via the active provider, and settles the reservation on success.
 * With the mock provider this endpoint simply acknowledges.
 */
export async function POST(req: Request) {
  const rawBody = await req.text();
  const signature = req.headers.get("stripe-signature");

  const event = getPaymentProvider().verifyWebhook(rawBody, signature);
  if (event.type === "paid" && event.reservationId) {
    await settleReservationPayment(event.reservationId);
  }
  return Response.json({ received: true });
}
