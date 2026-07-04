import "server-only";
import Stripe from "stripe";
import type {
  CheckoutInput,
  CheckoutResult,
  PaymentProvider,
  WebhookResult,
} from "./provider";

/** Production adapter — used when STRIPE_SECRET_KEY is set. */
export function createStripeProvider(secretKey: string): PaymentProvider {
  const stripe = new Stripe(secretKey);
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  return {
    name: "stripe",
    async createCheckout(input: CheckoutInput): Promise<CheckoutResult> {
      const session = await stripe.checkout.sessions.create({
        mode: "payment",
        success_url: input.successUrl,
        cancel_url: input.cancelUrl,
        client_reference_id: input.reservationId,
        line_items: [
          {
            quantity: 1,
            price_data: {
              currency: input.currency.toLowerCase(),
              unit_amount: Math.round(input.amount * 100),
              product_data: { name: input.description },
            },
          },
        ],
        metadata: { reservationId: input.reservationId },
      });
      return {
        sessionId: session.id,
        url: session.url ?? undefined,
        status: "requires_payment",
      };
    },
    verifyWebhook(rawBody: string, signature: string | null): WebhookResult {
      if (!webhookSecret || !signature) return { type: "ignored" };
      let event: Stripe.Event;
      try {
        event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
      } catch {
        return { type: "ignored" };
      }
      if (event.type === "checkout.session.completed") {
        const s = event.data.object as Stripe.Checkout.Session;
        return {
          type: "paid",
          reservationId:
            (s.metadata?.reservationId as string | undefined) ??
            s.client_reference_id ??
            undefined,
        };
      }
      if (event.type === "checkout.session.expired") {
        return { type: "failed" };
      }
      return { type: "ignored" };
    },
  };
}
