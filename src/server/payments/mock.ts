import "server-only";
import type {
  CheckoutInput,
  CheckoutResult,
  PaymentProvider,
  WebhookResult,
} from "./provider";

/**
 * Default provider when Stripe is not configured. Settles the payment inline
 * (status "paid") so the checkout flow completes in dev without real charges.
 */
export const mockPaymentProvider: PaymentProvider = {
  name: "mock",
  async createCheckout(input: CheckoutInput): Promise<CheckoutResult> {
    return {
      sessionId: `mock_${input.reservationId}_${Date.now()}`,
      status: "paid",
    };
  },
  verifyWebhook(): WebhookResult {
    return { type: "ignored" };
  },
};
