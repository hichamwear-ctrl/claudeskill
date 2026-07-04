/**
 * Payment provider abstraction (Phase 3).
 * Stripe is the production adapter; a mock adapter runs by default so the full
 * checkout flow works end-to-end without keys (no real charges). Swap by
 * implementing `PaymentProvider` — API routes and UI never change.
 */
export interface CheckoutInput {
  reservationId: string;
  amount: number; // EUR
  currency: string;
  description: string;
  successUrl: string;
  cancelUrl: string;
}

export interface CheckoutResult {
  sessionId: string;
  /** Redirect URL for hosted checkout (Stripe). Absent when settled inline. */
  url?: string;
  status: "requires_payment" | "paid";
}

export interface WebhookResult {
  type: "paid" | "failed" | "ignored";
  reservationId?: string;
}

export interface PaymentProvider {
  readonly name: string;
  createCheckout(input: CheckoutInput): Promise<CheckoutResult>;
  verifyWebhook(rawBody: string, signature: string | null): WebhookResult;
}
